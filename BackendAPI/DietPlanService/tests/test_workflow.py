# DietPlanService/tests/test_workflow.py
import pytest

from db import SessionLocal
from agents import NutritionAnalystAgent, NutritionAnalystInput
from workflow import call_tool, run_workflow
from conftest import VALID_PREFS, make_meals, expected_target_calories

TARGET_CALORIES = expected_target_calories(VALID_PREFS)


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.mark.asyncio
async def test_call_tool_refuses_disallowed_tool():
    events = []
    analyst = NutritionAnalystAgent()
    result = await call_tool(analyst, "generate_meals", NutritionAnalystInput(prefs=VALID_PREFS), events, step=1)
    assert result["ok"] is False
    assert "not permitted" in result["error"]
    assert events[0]["ok"] is False
    assert events[0]["tool"] == "generate_meals"


@pytest.mark.asyncio
async def test_run_workflow_happy_path_completes(mock_generate_meals, db_session):
    good_meals = make_meals(calories_each=TARGET_CALORIES / 4, count=4)
    mock_generate_meals.return_value = {"meals": good_meals, "withinTolerance": True}

    wf = await run_workflow("generate_diet_plan", dict(VALID_PREFS), user_id=1, session=db_session)

    assert wf.status == "completed"
    assert wf.approval_status == "auto_approved"
    assert wf.risk_level == "low"
    assert len(wf.events) >= 3  # calculate_targets (+risk assessed inline), generate_meals, validate_plan


@pytest.mark.asyncio
async def test_run_workflow_revise_then_pass(mock_generate_meals, db_session):
    bad_meals = make_meals(calories_each=(TARGET_CALORIES * 1.18) / 4, count=4)  # ~18% over -> revise
    good_meals = make_meals(calories_each=TARGET_CALORIES / 4, count=4)
    mock_generate_meals.side_effect = [
        {"meals": bad_meals, "withinTolerance": False},
        {"meals": good_meals, "withinTolerance": True},
    ]

    wf = await run_workflow("generate_diet_plan", dict(VALID_PREFS), user_id=1, session=db_session)

    assert wf.retry_count == 1
    assert wf.status == "completed"


@pytest.mark.asyncio
async def test_run_workflow_retry_limit_gives_failed(mock_generate_meals, db_session):
    bad_meals = make_meals(calories_each=(TARGET_CALORIES * 1.18) / 4, count=4)  # ~18% over -> always revise, never reject
    mock_generate_meals.return_value = {"meals": bad_meals, "withinTolerance": False}

    wf = await run_workflow("generate_diet_plan", dict(VALID_PREFS), user_id=1, session=db_session)

    assert wf.status == "failed"
    assert wf.retry_count == 3  # incremented past _MAX_REVISE_RETRIES (2) before giving up


@pytest.mark.asyncio
async def test_run_workflow_reject_stops_immediately(mock_generate_meals, db_session):
    meals = make_meals(calories_each=TARGET_CALORIES / 4, name="Grilled chicken breast", count=4)
    mock_generate_meals.return_value = {"meals": meals, "withinTolerance": True}
    prefs = dict(VALID_PREFS, restrictions=["vegetarian"])

    wf = await run_workflow("generate_diet_plan", prefs, user_id=1, session=db_session)

    assert wf.status == "rejected"
    assert wf.retry_count == 0
    assert mock_generate_meals.call_count == 1
