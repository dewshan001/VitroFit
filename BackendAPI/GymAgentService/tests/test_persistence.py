"""Persistence of workflows, steps, tool calls and approval fields."""

import asyncio

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.utils.db import SessionLocal
from src.models.db_models import GymWorkflow, GymWorkflowStep, GymWorkflowToolCall
from src.agent.store import WorkflowStore
from tests.support import FakeModel, gym_request
from tests.test_workflow import decide, make_runner, run, start


def steps_of(wid):
    with SessionLocal() as s:
        return list(
            s.scalars(select(GymWorkflowStep).where(GymWorkflowStep.workflow_id == wid).order_by(GymWorkflowStep.seq))
        )


def calls_of(wid):
    with SessionLocal() as s:
        return list(s.scalars(select(GymWorkflowToolCall).where(GymWorkflowToolCall.workflow_id == wid)))


def test_steps_and_tool_calls_are_stored_in_their_own_tables():
    async def scenario():
        runner = make_runner(FakeModel())
        wid = await start(runner)
        await decide(runner, wid, kind="approve", reason="ok")
        return wid

    wid = run(scenario())
    steps = steps_of(wid)
    assert [s.seq for s in steps] == list(range(1, len(steps) + 1))
    assert [s.agent for s in steps] == [
        "planner", "gym_analysis", "workout_recommendation", "validator", "approval_gate", "publish"
    ]
    assert all(s.ok and s.duration_ms >= 0 and s.summary for s in steps)

    by_id = {s.id: s.agent for s in steps}
    calls = calls_of(wid)
    assert {(by_id[c.step_id], c.tool) for c in calls} == {
        ("gym_analysis", "scrape_gym_website"),
        ("workout_recommendation", "list_equipment_taxonomy"),
    }
    scrape = next(c for c in calls if c.tool == "scrape_gym_website")
    assert scrape.ok and scrape.error_code is None and scrape.input_summary == "https://fitzone.lk"


def test_failed_tool_call_is_persisted_with_its_error_code():
    calls = [{"name": "scrape_gym_website", "args": {"url": "http://169.254.169.254/"}, "id": "c1", "type": "tool_call"}]

    async def scenario():
        return await start(make_runner(FakeModel(tool_calls=calls)))

    wid = run(scenario())
    bad = [c for c in calls_of(wid) if not c.ok]
    assert {(c.tool, c.error_code) for c in bad} == {("scrape_gym_website", "TARGET_NOT_ALLOWED")}


def test_approval_fields_are_persisted_on_approve():
    async def scenario():
        runner = make_runner(FakeModel())
        wid = await start(runner)
        pending = WorkflowStore().get(wid)
        assert pending["approvalStatus"] == "pending" and pending["decidedAt"] is None
        await decide(runner, wid, kind="approve", role="Admin", reason="Verified on site")
        return wid

    wid = run(scenario())
    with SessionLocal() as s:
        row = s.get(GymWorkflow, wid)
        assert (row.status, row.approval_status) == ("Published", "approved")
        assert (row.approved_by, row.approver_role, row.approval_note) == ("owner-9", "Admin", "Verified on site")
        assert row.decided_at is not None


def test_approval_fields_are_persisted_on_reject():
    async def scenario():
        runner = make_runner(FakeModel())
        wid = await start(runner)
        await decide(runner, wid, kind="reject", role="Gym_Owner", reason="Wrong gym")
        return wid

    wid = run(scenario())
    with SessionLocal() as s:
        row = s.get(GymWorkflow, wid)
        assert (row.status, row.approval_status, row.approver_role) == ("Rejected", "rejected", "Gym_Owner")
        assert row.approval_note == "Wrong gym" and row.decided_at is not None


def test_get_returns_steps_and_tool_calls_for_the_admin_view():
    async def scenario():
        return await start(make_runner(FakeModel()))

    wid = run(scenario())
    detail = WorkflowStore().get(wid)
    assert [s["agent"] for s in detail["completedSteps"]] == ["planner", "gym_analysis", "workout_recommendation", "validator"]
    assert {c["tool"] for c in detail["toolResults"]} == {"scrape_gym_website", "list_equipment_taxonomy"}
    assert all(c["stepId"] in {s["id"] for s in detail["completedSteps"]} for c in detail["toolResults"])


def test_node_record_is_all_or_nothing():
    store = WorkflowStore()
    wid = store.create(gym_request().model_dump(mode="json"), "user-1")
    broken_call = {"agent": "gym_analysis"}  # missing "tool" -> KeyError mid-transaction
    with pytest.raises(KeyError):
        store.record_node(
            wid, "gym_analysis", ok=True, duration_ms=1, error=None, summary="x",
            tool_calls=[broken_call], delta={"status": "AwaitingApproval"},
        )
    assert steps_of(wid) == []                      # step row rolled back
    assert store.get(wid)["status"] == "Running"    # state delta rolled back


def test_step_sequence_is_unique_per_workflow():
    store = WorkflowStore()
    wid = store.create(gym_request().model_dump(mode="json"), "user-1")
    with SessionLocal() as s:
        s.add(GymWorkflowStep(workflow_id=wid, seq=1, agent="planner", ok=True))
        s.add(GymWorkflowStep(workflow_id=wid, seq=1, agent="planner", ok=True))
        with pytest.raises(IntegrityError):
            s.commit()


def test_deleting_a_workflow_cascades_to_steps_and_tool_calls():
    async def scenario():
        return await start(make_runner(FakeModel()))

    wid = run(scenario())
    assert steps_of(wid) and calls_of(wid)
    with SessionLocal() as s:
        s.delete(s.get(GymWorkflow, wid))
        s.commit()
    assert steps_of(wid) == [] and calls_of(wid) == []


def test_orphan_step_is_rejected_by_the_foreign_key():
    with SessionLocal() as s:
        s.add(GymWorkflowStep(workflow_id="no-such-workflow", seq=1, agent="planner", ok=True))
        with pytest.raises(IntegrityError):
            s.commit()
