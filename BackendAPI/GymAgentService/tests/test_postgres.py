"""Real-PostgreSQL checks. Skipped unless TEST_DATABASE_URL points at a Postgres test DB:

    TEST_DATABASE_URL=postgresql+psycopg2://user:pw@localhost:5432/gym_test pytest tests/test_postgres.py
"""

import asyncio
import os
import sys

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from src.models.contracts import ApprovalDecision
from src.utils.db import DATABASE_URL, SessionLocal, engine
from src.agent.graph import build_graph
from src.models.db_models import GymDetails
from src.agent.runner import WorkflowRunner
from src.agent.store import WorkflowStore
from tests.support import FakeModel, gym_request

pytestmark = [
    pytest.mark.postgres,
    pytest.mark.skipif(not DATABASE_URL.startswith("postgresql"), reason="needs TEST_DATABASE_URL pointing at PostgreSQL"),
]


def run_selector(coro):
    """psycopg async needs a selector event loop on Windows."""
    if sys.platform == "win32":
        return asyncio.run(coro, loop_factory=asyncio.SelectorEventLoop)
    return asyncio.run(coro)


def test_schema_has_expected_tables_types_and_constraints():
    insp = inspect(engine)
    assert {"gym_agent_workflows", "gym_agent_steps", "gym_agent_tool_calls"} <= set(insp.get_table_names())

    cols = {c["name"]: str(c["type"]) for c in insp.get_columns("gym_agent_workflows")}
    assert cols["plan"] == "JSONB" and cols["facts"] == "JSONB"
    assert {"approval_status", "approved_by", "approver_role", "approval_note", "decided_at"} <= set(cols)

    step_fks = insp.get_foreign_keys("gym_agent_steps")
    assert step_fks[0]["referred_table"] == "gym_agent_workflows"
    assert step_fks[0]["options"].get("ondelete") == "CASCADE"
    call_fks = {fk["referred_table"] for fk in insp.get_foreign_keys("gym_agent_tool_calls")}
    assert call_fks == {"gym_agent_workflows", "gym_agent_steps"}

    assert any(u["name"] == "uq_gym_step_workflow_seq" for u in insp.get_unique_constraints("gym_agent_steps"))
    assert {c["name"] for c in insp.get_check_constraints("gym_agent_workflows")} == {
        "ck_gym_workflow_status",
        "ck_gym_workflow_approval",
    }


def test_paused_approval_survives_restart_with_the_real_postgres_checkpointer(monkeypatch):
    monkeypatch.setenv("GYM_CHECKPOINTER", "postgres")
    from src.agent.checkpointer import open_checkpointer

    async def scenario():
        store = WorkflowStore()
        async with open_checkpointer() as saver:
            first = WorkflowRunner(store, build_graph(store, FakeModel(), saver, None), budget_seconds=30)
            wid = await first.start(gym_request(), "user-1")
            await first.drain()
        assert store.get(wid)["status"] == "AwaitingApproval"

        # Connection closed = process gone. A fresh saver/graph/runner must resume from Postgres alone.
        async with open_checkpointer() as saver:
            second = WorkflowRunner(store, build_graph(store, FakeModel(), saver, None), budget_seconds=30)
            await second.decide(
                wid, ApprovalDecision(decision="approve", reason="ok", actor_id="admin-1", actor_role="Admin")
            )
            await second.drain()
        return wid

    wid = run_selector(scenario())
    detail = WorkflowStore().get(wid)
    assert detail["status"] == "Published" and detail["approverRole"] == "Admin"
    with SessionLocal() as s:
        assert s.get(GymDetails, "place-1").source == "verified"
    assert [x["agent"] for x in detail["completedSteps"]][-2:] == ["approval_gate", "publish"]


# ── upgrade of a database created before provenance existed ─────────────


def _downgrade_to_old_shape():
    """Recreate the table as an earlier version left it: no provenance columns or constraints."""
    from sqlalchemy import text

    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE gym_agent_details DROP CONSTRAINT ck_gym_details_verified_has_workflow"))
        conn.execute(text("ALTER TABLE gym_agent_details DROP CONSTRAINT fk_gym_details_verified_workflow"))
        conn.execute(text(
            "ALTER TABLE gym_agent_details DROP COLUMN verified_workflow_id, "
            "DROP COLUMN verified_by, DROP COLUMN verified_at"
        ))


def _insert_old_verified_gym(conn, place_id):
    from sqlalchemy import text

    conn.execute(
        text(
            "INSERT INTO gym_agent_details (place_id, name, source, equipment, classes) "
            "VALUES (:p, 'Old Gym', 'verified', '[\"treadmill\"]', '[]')"
        ),
        {"p": place_id},
    )


def test_migration_upgrades_an_old_database_and_is_idempotent():
    from datetime import datetime, timezone

    from sqlalchemy import text

    from src.utils.db_migrations import ensure_gym_details_provenance
    from src.models.db_models import GymDetails, GymWorkflow

    _downgrade_to_old_shape()
    with SessionLocal() as s:
        s.add(GymWorkflow(
            id="wf-old", place_id="linked", requested_by="u", objective="o", status="Published", request={},
            approval_status="approved", approved_by="admin-6", approver_role="Admin",
            decided_at=datetime(2026, 9, 30, 1, 0, tzinfo=timezone.utc),
        ))
        s.commit()
    with engine.begin() as conn:
        _insert_old_verified_gym(conn, "linked")     # has a Published workflow behind it
        _insert_old_verified_gym(conn, "orphan")     # verified by hand, no workflow

    ensure_gym_details_provenance(engine)
    ensure_gym_details_provenance(engine)            # second run must change nothing and not fail

    with SessionLocal() as s:
        linked = s.get(GymDetails, "linked")
        assert (linked.verified_workflow_id, linked.verified_by) == ("wf-old", "admin-6")
        assert linked.verified_at == datetime(2026, 9, 30, 1, 0, tzinfo=timezone.utc)
        orphan = s.get(GymDetails, "orphan")
        assert orphan.source == "verified" and orphan.verified_workflow_id is None   # left as it was

    with engine.connect() as conn:
        rows = dict(conn.execute(text(
            "SELECT conname, convalidated FROM pg_constraint WHERE conrelid = 'gym_agent_details'::regclass "
            "AND conname IN ('ck_gym_details_verified_has_workflow','fk_gym_details_verified_workflow')"
        )).all())
    assert rows == {"ck_gym_details_verified_has_workflow": False, "fk_gym_details_verified_workflow": True}

    # NOT VALID still protects every new write...
    with SessionLocal() as s:
        s.add(GymDetails(place_id="fresh", name="n", source="verified", equipment=[], classes=[]))
        with pytest.raises(IntegrityError):
            s.commit()
    # ...and every change to an existing row, including one that would keep it un-linked.
    with SessionLocal() as s:
        s.get(GymDetails, "orphan").equipment = ["changed"]
        with pytest.raises(IntegrityError):
            s.commit()


def test_migration_is_a_no_op_on_a_current_database():
    from sqlalchemy import inspect

    from src.utils.db_migrations import ensure_gym_details_provenance

    before = {c["name"] for c in inspect(engine).get_columns("gym_agent_details")}
    ensure_gym_details_provenance(engine)
    assert {c["name"] for c in inspect(engine).get_columns("gym_agent_details")} == before


def test_guard_flags_column_is_added_to_an_old_tool_calls_table_and_the_migration_is_idempotent():
    from sqlalchemy import text

    from src.utils.db_migrations import ensure_tool_call_guard_flags

    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE gym_agent_tool_calls DROP COLUMN guard_flags"))
    assert "guard_flags" not in {c["name"] for c in inspect(engine).get_columns("gym_agent_tool_calls")}

    ensure_tool_call_guard_flags(engine)
    ensure_tool_call_guard_flags(engine)                      # second run: nothing to do, no error

    columns = {c["name"]: c for c in inspect(engine).get_columns("gym_agent_tool_calls")}
    assert "guard_flags" in columns and columns["guard_flags"]["nullable"] is True
    assert "VARCHAR(200)" in str(columns["guard_flags"]["type"])
