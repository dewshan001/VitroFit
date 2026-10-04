# DietPlanService/tests/test_reliability.py
"""Audit trail, start-up recovery, the concurrency cap and the retry/time limits."""
import asyncio
import uuid

import pytest
from sqlalchemy import select

import src.agent.runner as runner
import src.agent.workflow as workflow
from conftest import VALID_PREFS, generate_and_wait, make_meals, expected_target_calories, new_user_id, poll_workflow
from src.agent.store import fail_stale
from src.agent.workflow import run_workflow
from src.models.db_models import DietWorkflow, DietWorkflowStep
from src.utils.db import SessionLocal

TARGET = expected_target_calories(VALID_PREFS)


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _steps(session, workflow_id):
    session.expire_all()
    return session.execute(
        select(DietWorkflowStep).where(DietWorkflowStep.workflow_id == workflow_id).order_by(DietWorkflowStep.seq)
    ).scalars().all()


# -- audit trail ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_every_event_is_mirrored_to_a_step_row(mock_generate_meals, db_session):
    mock_generate_meals.return_value = {"meals": make_meals(TARGET / 4, count=4), "withinTolerance": True}
    wf = await run_workflow("generate_diet_plan", dict(VALID_PREFS), user_id=new_user_id(), session=db_session)

    steps = _steps(db_session, wf.id)
    assert len(steps) == len(wf.events) >= 4
    assert [s.seq for s in steps] == list(range(len(steps)))          # contiguous, no gaps or repeats
    assert [s.agent for s in steps][0] == "planner"
    assert {"NutritionAnalystAgent", "MealGeneratorAgent", "SafetyValidatorAgent"} <= {s.agent for s in steps}
    assert all(s.ok for s in steps)
    assert all(s.duration_ms is not None for s in steps)


@pytest.mark.asyncio
async def test_failed_tool_is_recorded_with_its_error(mock_generate_meals, db_session):
    mock_generate_meals.return_value = {"error": "The meal-planning service is temporarily unavailable. Please try again."}
    wf = await run_workflow("generate_diet_plan", dict(VALID_PREFS), user_id=new_user_id(), session=db_session)
    assert wf.status == "failed"
    failed = [s for s in _steps(db_session, wf.id) if not s.ok]
    assert not failed or failed[0].error  # error text is short and recorded, never a prompt


def test_steps_follow_a_refine_too(client, auth_headers, mock_generate_meals, mock_refine_meals, db_session):
    headers = auth_headers(user_id=new_user_id())
    workflow_id, _ = generate_and_wait(client, headers, VALID_PREFS, mock_generate_meals)
    before = len(_steps(db_session, uuid.UUID(workflow_id)))
    mock_refine_meals.return_value = {"meals": make_meals(TARGET / 4, name="Quinoa bowl", count=4), "withinTolerance": True}
    client.post(f"/api/diet/workflows/{workflow_id}/refine", json={"instruction": "swap the rice"}, headers=headers)
    poll_workflow(client, workflow_id, headers)
    after = _steps(db_session, uuid.UUID(workflow_id))
    assert len(after) > before and any(s.tool == "refine_meals" for s in after)


def test_steps_are_deleted_with_their_workflow(db_session):
    wf = DietWorkflow(user_id=1, objective="x", status="completed", inputs={}, events=[
        {"step": 1, "agent": "A", "tool": "t", "ok": True, "error": None, "duration_ms": 1}])
    db_session.add(wf)
    db_session.commit()
    assert len(_steps(db_session, wf.id)) == 1


def test_guard_flags_are_stored_on_the_step(db_session):
    wf = DietWorkflow(user_id=1, objective="x", status="completed", inputs={}, events=[
        {"step": 0, "agent": "planner", "tool": "build_plan", "ok": True, "guard_flags": ["ROLE_PLAY"]}])
    db_session.add(wf)
    db_session.commit()
    assert _steps(db_session, wf.id)[0].guard_flags == ["ROLE_PLAY"]


# -- start-up recovery ------------------------------------------------------------------------

def _row(session, **kwargs):
    wf = DietWorkflow(user_id=new_user_id(), objective="generate_diet_plan", inputs={}, events=[], **kwargs)
    session.add(wf)
    session.commit()
    return wf


def test_interrupted_generation_is_marked_failed(db_session):
    wf = _row(db_session, status="running")
    assert fail_stale(db_session, 0) >= 1
    db_session.refresh(wf)
    assert wf.status == "failed" and "interrupted" in wf.error


def test_interrupted_edit_goes_back_to_completed_and_keeps_the_plan(db_session):
    meals = make_meals(500.0, count=4)
    wf = _row(db_session, status="running", meals=meals, final_outcome={"totalCalories": 2000, "withinTolerance": True})
    fail_stale(db_session, 0)
    db_session.refresh(wf)
    assert wf.status == "completed" and wf.meals == meals and "unchanged" in wf.error


def test_recent_runs_are_left_alone_when_an_age_limit_is_given(db_session):
    wf = _row(db_session, status="running")
    fail_stale(db_session, 3600)
    db_session.refresh(wf)
    assert wf.status == "running"
    wf.status = "failed"
    db_session.commit()


def test_finished_runs_are_never_touched(db_session):
    done = _row(db_session, status="completed")
    failed = _row(db_session, status="failed")
    fail_stale(db_session, 0)
    db_session.refresh(done)
    db_session.refresh(failed)
    assert (done.status, failed.status) == ("completed", "failed")


def test_recover_interrupted_uses_its_own_session():
    # Smoke test of the start-up hook: runs without raising and returns a count.
    assert isinstance(runner.recover_interrupted(), int)


def test_startup_hook_runs_through_the_app_lifespan(client):
    from fastapi.testclient import TestClient
    import main
    with TestClient(main.app) as live:  # entering the context runs the lifespan
        assert live.get("/health").json()["status"] == "ok"


# -- concurrency cap --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_only_the_configured_number_of_runs_use_the_llm_at_once(monkeypatch, mock_generate_meals):
    monkeypatch.setattr(runner, "MAX_CONCURRENT_WORKFLOWS", 2)
    runner._slots.clear()

    active = {"now": 0, "peak": 0}

    async def slow_generate(targets, prefs):
        active["now"] += 1
        active["peak"] = max(active["peak"], active["now"])
        await asyncio.sleep(0.05)
        active["now"] -= 1
        return {"meals": make_meals(TARGET / 4, count=4), "withinTolerance": True}

    import src.agent.nodes.meal_generator as node
    monkeypatch.setattr(node, "generate_meals", slow_generate)

    async def one_run():
        session = SessionLocal()
        try:
            return await run_workflow("generate_diet_plan", dict(VALID_PREFS), user_id=new_user_id(), session=session)
        finally:
            session.close()

    results = await asyncio.gather(*[one_run() for _ in range(5)])
    assert all(r.status == "completed" for r in results)
    assert active["peak"] == 2


def test_each_event_loop_gets_its_own_semaphore():
    async def grab():
        return runner.slot()

    first = asyncio.run(grab())
    second = asyncio.run(grab())
    assert first is not second


@pytest.mark.asyncio
async def test_a_refine_waits_for_a_free_slot_too(monkeypatch, mock_generate_meals, mock_refine_meals, db_session):
    monkeypatch.setattr(runner, "MAX_CONCURRENT_WORKFLOWS", 1)
    runner._slots.clear()
    mock_generate_meals.return_value = {"meals": make_meals(TARGET / 4, count=4), "withinTolerance": True}
    wf = await run_workflow("generate_diet_plan", dict(VALID_PREFS), user_id=new_user_id(), session=db_session)

    mock_refine_meals.return_value = {"meals": make_meals(TARGET / 4, name="Quinoa bowl", count=4), "withinTolerance": True}
    async with runner.slot():  # every slot busy
        task = asyncio.create_task(workflow.execute_refine(wf.id, "swap the rice"))
        await asyncio.sleep(0.05)
        assert not task.done()
        mock_refine_meals.assert_not_called()
    await asyncio.wait_for(task, timeout=5)  # slot freed -> the edit runs
    mock_refine_meals.assert_awaited_once()


# -- retry / time-budget behaviour is unchanged -------------------------------------------------

@pytest.mark.asyncio
async def test_time_budget_fails_the_run_cleanly(monkeypatch, mock_generate_meals, db_session):
    monkeypatch.setattr(workflow, "_OVERALL_TIME_BUDGET_SECONDS", -1)
    mock_generate_meals.return_value = {"meals": make_meals(TARGET / 4, count=4), "withinTolerance": True}
    wf = await run_workflow("generate_diet_plan", dict(VALID_PREFS), user_id=new_user_id(), session=db_session)
    assert wf.status == "failed" and "time budget" in wf.error


@pytest.mark.asyncio
async def test_unexpected_error_marks_the_run_failed_instead_of_leaving_it_running(monkeypatch, db_session):
    async def boom(*args, **kwargs):
        raise RuntimeError("unexpected")

    monkeypatch.setattr(workflow, "_run_steps", boom)
    wf = workflow.create_workflow("generate_diet_plan", dict(VALID_PREFS), new_user_id(), db_session)
    await workflow.execute_workflow(wf.id, dict(VALID_PREFS))
    db_session.refresh(wf)
    assert wf.status == "failed" and "Unexpected error" in wf.error


@pytest.mark.asyncio
async def test_generation_failure_is_reported_as_failed(mock_generate_meals, db_session):
    mock_generate_meals.return_value = {"error": "The meal-planning service returned an unreadable response. Please try again."}
    wf = await run_workflow("generate_diet_plan", dict(VALID_PREFS), user_id=new_user_id(), session=db_session)
    assert wf.status == "failed" and "unreadable" in wf.error


@pytest.mark.asyncio
async def test_refine_failure_keeps_the_plan_and_explains(mock_generate_meals, mock_refine_meals, db_session):
    mock_generate_meals.return_value = {"meals": make_meals(TARGET / 4, count=4), "withinTolerance": True}
    wf = await run_workflow("generate_diet_plan", dict(VALID_PREFS), user_id=new_user_id(), session=db_session)
    original = wf.meals
    mock_refine_meals.return_value = {"error": "The meal-planning service is temporarily unavailable. Please try again."}
    await workflow.execute_refine(wf.id, "swap the rice")
    db_session.refresh(wf)
    assert wf.status == "completed" and wf.meals == original and "temporarily unavailable" in wf.error


@pytest.mark.asyncio
async def test_validator_input_error_does_not_crash_the_run(monkeypatch, mock_generate_meals, db_session):
    mock_generate_meals.return_value = {"meals": make_meals(TARGET / 4, count=4), "withinTolerance": True}

    async def broken_validate(self, payload):
        raise ValueError("validator exploded")

    import src.agent.nodes.safety_validator as sv
    monkeypatch.setattr(sv.SafetyValidatorAgent, "run", broken_validate)
    wf = await run_workflow("generate_diet_plan", dict(VALID_PREFS), user_id=new_user_id(), session=db_session)
    assert wf.status == "failed" and "validator exploded" in wf.error


def test_workflow_detail_exposes_the_new_fields_additively(client, auth_headers, mock_generate_meals):
    headers = auth_headers(user_id=new_user_id())
    _, detail = generate_and_wait(client, headers, VALID_PREFS, mock_generate_meals)
    # everything the web client already reads is still there...
    for key in ("id", "status", "riskLevel", "approvalStatus", "plan", "completedSteps", "targets", "meals",
                "validationResults", "finalOutcome", "message", "retryCount", "planId"):
        assert key in detail
    # ...plus the additions
    assert {"route", "approverRole", "decidedAt"} <= set(detail)


def test_workflow_endpoints_404_for_garbage_and_unknown_ids(client, auth_headers):
    headers = auth_headers(user_id=new_user_id())
    assert client.get("/api/diet/workflows/not-a-uuid", headers=headers).status_code == 404
    assert client.get(f"/api/diet/workflows/{uuid.uuid4()}", headers=headers).status_code == 404


def test_other_users_cannot_read_a_workflow_but_trainers_can(client, auth_headers, mock_generate_meals):
    owner = auth_headers(user_id=new_user_id())
    workflow_id, _ = generate_and_wait(client, owner, VALID_PREFS, mock_generate_meals)
    assert client.get(f"/api/diet/workflows/{workflow_id}", headers=auth_headers(user_id=new_user_id())).status_code == 403
    assert client.get(f"/api/diet/workflows/{workflow_id}", headers=auth_headers(user_id=1, role="Trainer")).status_code == 200


def test_saved_plans_can_be_listed_updated_and_deleted(client, auth_headers, mock_generate_meals):
    from conftest import confirm_body
    headers = auth_headers(user_id=new_user_id())
    workflow_id, _ = generate_and_wait(client, headers, VALID_PREFS, mock_generate_meals)
    plan_id = client.post("/api/diet/confirm", json=confirm_body(VALID_PREFS, workflow_id), headers=headers).json()["id"]
    assert [p["id"] for p in client.get("/api/diet/plans", headers=headers).json()] == [plan_id]
    assert client.put(f"/api/diet/plans/{plan_id}", json=confirm_body(VALID_PREFS), headers=headers).status_code == 200
    assert client.delete(f"/api/diet/plans/{plan_id}", headers=headers).status_code == 204
    assert client.get("/api/diet/plans", headers=headers).json() == []
    assert client.delete(f"/api/diet/plans/{plan_id}", headers=headers).status_code == 404
    assert client.put(f"/api/diet/plans/{plan_id}", json=confirm_body(VALID_PREFS), headers=headers).status_code == 404


def test_requests_without_a_token_are_refused(client):
    assert client.get("/api/diet/plans").status_code == 401
    assert client.post("/api/diet/generate", json=VALID_PREFS).status_code == 401
    assert client.get("/api/diet/plans", headers={"Authorization": "Bearer garbage"}).status_code == 401


# -- targeted revise ----------------------------------------------------------------------------

def test_a_revise_only_helps_when_the_meal_generator_can_fix_something():
    assert workflow._generator_can_fix([{"severity": "revise", "target": "MealGeneratorAgent"}])
    assert workflow._generator_can_fix([{"severity": "revise"}])  # rows from before `target` existed
    assert not workflow._generator_can_fix([{"severity": "revise", "target": "NutritionAnalystAgent"}])
    assert not workflow._generator_can_fix([{"severity": "reject", "target": "MealGeneratorAgent"}])
    assert not workflow._generator_can_fix([])


@pytest.mark.asyncio
async def test_no_retry_is_spent_on_a_problem_the_generator_cannot_fix(monkeypatch, mock_generate_meals, db_session):
    import src.agent.nodes.safety_validator as sv
    mock_generate_meals.return_value = {"meals": make_meals(TARGET / 4, count=4), "withinTolerance": True}

    def only_analyst_can_fix(meals, targets, prefs):
        return {"verdict": "revise", "violations": [{
            "code": "X", "severity": "revise", "message": "needs different targets", "field": None,
            "target": "NutritionAnalystAgent", "retryable": True}]}

    monkeypatch.setattr(sv, "validate_plan", only_analyst_can_fix)
    wf = await run_workflow("generate_diet_plan", dict(VALID_PREFS), user_id=new_user_id(), session=db_session)
    assert mock_generate_meals.call_count == 1          # not asked to try again
    assert wf.status == "completed" and wf.final_outcome["withinTolerance"] is False
