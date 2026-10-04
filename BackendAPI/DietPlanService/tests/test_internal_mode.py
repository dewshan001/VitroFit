# DietPlanService/tests/test_internal_mode.py
"""DIET_AGENT_KEY turns on internal-only access (only the ASP.NET API can call the
service); unset, the service behaves exactly as it always did."""
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from conftest import VALID_PREFS, new_user_id
from src.models.db_models import DietWorkflow
from src.utils import db_migrations
from src.utils.logger import log_event, safe

KEY = "k" * 40


def test_without_a_key_configured_nothing_changes(client, auth_headers, monkeypatch):
    monkeypatch.delenv("DIET_AGENT_KEY", raising=False)
    assert client.get("/api/diet/plans", headers=auth_headers(user_id=new_user_id())).status_code == 200


def test_with_a_key_the_header_is_required(client, auth_headers, monkeypatch):
    monkeypatch.setenv("DIET_AGENT_KEY", KEY)
    headers = auth_headers(user_id=new_user_id())
    assert client.get("/api/diet/plans", headers=headers).status_code == 401
    assert client.get("/api/diet/plans", headers={**headers, "X-Diet-Agent-Key": "wrong" * 8}).status_code == 401
    assert client.get("/api/diet/plans", headers={**headers, "X-Diet-Agent-Key": KEY}).status_code == 200


def test_the_key_does_not_replace_the_user_token(client, monkeypatch):
    monkeypatch.setenv("DIET_AGENT_KEY", KEY)
    assert client.get("/api/diet/plans", headers={"X-Diet-Agent-Key": KEY}).status_code == 401  # no JWT


def test_a_key_that_is_too_short_fails_closed(client, auth_headers, monkeypatch):
    monkeypatch.setenv("DIET_AGENT_KEY", "short")
    headers = {**auth_headers(user_id=new_user_id()), "X-Diet-Agent-Key": "short"}
    assert client.get("/api/diet/plans", headers=headers).status_code == 503


def test_health_and_docs_stay_open(client, monkeypatch):
    monkeypatch.setenv("DIET_AGENT_KEY", KEY)
    assert client.get("/health").status_code == 200
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_every_diet_route_is_protected_by_the_key(client, auth_headers, monkeypatch):
    monkeypatch.setenv("DIET_AGENT_KEY", KEY)
    headers = auth_headers(user_id=new_user_id(), role="Admin")
    wf = "00000000-0000-0000-0000-000000000000"
    calls = [
        ("get", "/api/diet/plans", None), ("post", "/api/diet/generate", VALID_PREFS),
        ("post", "/api/diet/confirm", {}), ("put", "/api/diet/plans/1", {}), ("delete", "/api/diet/plans/1", None),
        ("get", "/api/diet/approvals/pending", None), ("post", f"/api/diet/workflows/{wf}/approve", None),
        ("post", f"/api/diet/workflows/{wf}/reject?note=x", None), ("get", f"/api/diet/workflows/{wf}", None),
        ("get", f"/api/diet/workflows/{wf}/trace", None), ("post", f"/api/diet/workflows/{wf}/refine", {"instruction": "x"}),
    ]
    for method, url, body in calls:
        resp = getattr(client, method)(url, headers=headers, **({"json": body} if body is not None else {}))
        assert resp.status_code == 401, (method, url, resp.status_code)


def test_allowed_hosts_can_be_restricted(monkeypatch):
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    from fastapi.middleware.trustedhost import TrustedHostMiddleware
    probe = FastAPI()
    probe.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost"])

    @probe.get("/x")
    def x():
        return {}

    assert TestClient(probe, base_url="http://localhost").get("/x").status_code == 200
    assert TestClient(probe, base_url="http://evil.example").get("/x").status_code == 400


# -- migrations and constraints ---------------------------------------------------------------

def _old_database():
    """A diet_workflows table as it was before route/approver_role/decided_at existed."""
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE diet_workflows (id CHAR(32) PRIMARY KEY, user_id INTEGER, objective VARCHAR(255), status VARCHAR(20))"))
    return engine


def test_missing_columns_are_added_to_an_old_table():
    engine = _old_database()
    db_migrations.ensure_workflow_columns(engine)
    cols = {c["name"] for c in inspect(engine).get_columns("diet_workflows")}
    assert {"route", "approver_role", "decided_at"} <= cols
    db_migrations.ensure_workflow_columns(engine)  # idempotent: second run changes nothing and does not fail


def test_migration_does_nothing_on_a_fresh_or_empty_database():
    db_migrations.ensure_workflow_columns(create_engine("sqlite://"))  # no table yet
    db_migrations.ensure_workflow_constraints(create_engine("sqlite://"))  # non-PostgreSQL: skipped


def test_constraints_are_added_with_the_right_sql_on_postgresql(monkeypatch):
    executed = []

    class FakeConn:
        def execute(self, statement, *args, **kwargs):
            sql = str(statement)
            executed.append(sql)
            return [("ck_diet_workflows_status",)] if "pg_constraint" in sql else []

    class FakeEngine:
        class dialect:
            name = "postgresql"

        def begin(self):
            conn = FakeConn()

            class Ctx:
                def __enter__(self_inner):
                    return conn

                def __exit__(self_inner, *exc):
                    return False

            return Ctx()

    db_migrations.ensure_workflow_constraints(FakeEngine())
    alters = [s for s in executed if s.startswith("ALTER TABLE")]
    assert len(alters) == 2 and all("NOT VALID" in s for s in alters)          # status already existed
    assert not any("ck_diet_workflows_status" in s for s in alters)


def test_database_refuses_an_invalid_status(db_session_factory):
    session = db_session_factory()
    session.add(DietWorkflow(user_id=1, objective="x", status="banana", inputs={}))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
    session.add(DietWorkflow(user_id=1, objective="x", status="running", inputs={}, approval_status="maybe"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
    session.add(DietWorkflow(user_id=1, objective="x", status="running", inputs={}, risk_level="extreme"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
    session.close()


@pytest.fixture
def db_session_factory():
    from src.utils.db import engine
    return sessionmaker(bind=engine)


# -- logging ------------------------------------------------------------------------------------

def test_safe_redacts_secrets_strips_control_characters_and_truncates():
    assert "nvapi" not in safe("key nvapi-ABCDEFGH12345678")
    assert safe("Authorization: Bearer abcdefghijklmnop") == "Authorization: [redacted]"
    assert safe("line1\nline2\r\x00end") == "line1 line2 end"
    long_text = "plain words " * 60
    assert safe(long_text).endswith("...") and len(safe(long_text)) == 160
    assert safe("x" * 500) == "[redacted]"  # a long unbroken run looks like an encoded secret
    assert safe(None) == "" and safe("café") == "caf?"
    assert "[redacted]" in safe("api_key=SECRETVALUE")
    assert "[redacted]" in safe("eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abcdefghijk")


def test_log_event_has_one_line_with_the_workflow_id(caplog):
    with caplog.at_level("INFO", logger="diet_agent"):
        log_event("tool end", "1a2b3c4d-0000-0000-0000-000000000000", agent="MealGeneratorAgent", ok=True, ms=12)
    line = caplog.records[-1].getMessage()
    assert line == "tool end wf=1a2b3c4d agent=MealGeneratorAgent ok=True ms=12"


def test_log_event_cannot_be_used_to_forge_log_lines(caplog):
    with caplog.at_level("INFO", logger="diet_agent"):
        log_event("tool end", None, error="boom\n2026-01-01 INFO [diet_agent] approval decided wf=forged")
    assert "\n" not in caplog.records[-1].getMessage()
