"""Real-PostgreSQL checks. Skipped unless TEST_DATABASE_URL points at a Postgres test DB:

    TEST_DATABASE_URL=postgresql+psycopg2://user:pw@localhost:5432/gym_test pytest tests/test_postgres.py
"""

import asyncio
import os
import sys

import pytest
from sqlalchemy import inspect

from contracts import ApprovalDecision
from db import DATABASE_URL, SessionLocal, engine
from graph import build_graph
from models import GymDetails
from runner import WorkflowRunner
from store import WorkflowStore
from tests.support import FakeModel, gym_request

pytestmark = pytest.mark.skipif(
    not DATABASE_URL.startswith("postgresql"), reason="needs TEST_DATABASE_URL pointing at PostgreSQL"
)


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
    from checkpointer import open_checkpointer

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
