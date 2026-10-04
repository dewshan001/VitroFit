# DietPlanService/tests/test_planner_and_registry.py
import pytest

from conftest import VALID_PREFS, HIGH_RISK_PREFS, make_meals, expected_target_calories
from src.agent.nodes import MealGeneratorAgent, NutritionAnalystAgent, SafetyValidatorAgent, planner
from src.agent.workflow import call_tool
from src.models.contracts import MealGeneratorInput, NutritionAnalystInput, PlanResult
from src.tools.tool_registry import TOOL_PERMISSIONS, is_allowed, tools_for


def test_plan_has_the_same_four_steps_the_frontend_renders():
    steps = planner.build_plan("generate_diet_plan", VALID_PREFS)
    assert [(s["step"], s["agent"], s["tool"], s["status"]) for s in steps] == [
        (1, "NutritionAnalystAgent", "calculate_targets", "pending"),
        (2, "NutritionAnalystAgent", "assess_risk", "pending"),
        (3, "MealGeneratorAgent", "generate_meals", "pending"),
        (4, "SafetyValidatorAgent", "validate_plan", "pending"),
    ]
    assert all(s["description"] for s in steps)
    assert "medical_review" not in steps[3]["description"]


def test_medical_conditions_add_a_note_to_the_validation_step():
    steps = planner.build_plan("generate_diet_plan", dict(VALID_PREFS, medicalConditions=["diabetes"]))
    assert "medical_review" in steps[3]["description"]


@pytest.mark.parametrize("prefs,route", [
    (VALID_PREFS, "standard"),
    (dict(VALID_PREFS, medicalConditions=["diabetes"]), "medical_review"),
    (dict(VALID_PREFS, age=16), "medical_review"),
    (HIGH_RISK_PREFS, "medical_review"),
])
def test_route_is_chosen_from_the_profile(prefs, route):
    assert planner.choose_route(prefs) == route
    result = planner.run("generate_diet_plan", prefs)
    assert isinstance(result, PlanResult) and result.route == route


def test_allowed_tools_follow_the_plan():
    plan = planner.build_plan("generate_diet_plan", VALID_PREFS)
    assert planner.allowed_tools_for(plan) == ["calculate_targets", "assess_risk", "generate_meals", "validate_plan"]
    assert "refine_meals" in planner.allowed_tools_for(plan, refine=True)
    assert planner.allowed_tools_for(None) is None  # rows from before the planner existed: role limits only


def test_registry_is_the_single_source_of_each_agents_tools():
    assert NutritionAnalystAgent.allowed_tools == ["calculate_targets", "assess_risk", "lookup_budget"]
    assert MealGeneratorAgent.allowed_tools == ["generate_meals", "refine_meals"]
    assert SafetyValidatorAgent.allowed_tools == ["validate_plan"]
    assert tools_for("NoSuchAgent") == []
    assert set(TOOL_PERMISSIONS) == {"NutritionAnalystAgent", "MealGeneratorAgent", "SafetyValidatorAgent"}


def test_is_allowed_checks_role_then_plan():
    assert is_allowed("MealGeneratorAgent", "generate_meals")
    assert not is_allowed("MealGeneratorAgent", "validate_plan")                 # wrong role
    assert not is_allowed("Nobody", "generate_meals")
    assert is_allowed("MealGeneratorAgent", "generate_meals", ["generate_meals"])
    assert not is_allowed("MealGeneratorAgent", "refine_meals", ["generate_meals"])  # role ok, plan says no


@pytest.mark.asyncio
async def test_call_tool_refuses_a_tool_the_plan_did_not_allow(mock_generate_meals):
    events = []
    payload = MealGeneratorInput(targets={"totalCalories": 2000, "macros": {}}, prefs=VALID_PREFS)
    result = await call_tool(MealGeneratorAgent(), "generate_meals", payload, events, step=3, allowed=["calculate_targets"])
    assert result["ok"] is False and "not permitted" in result["error"]
    assert events[0]["ok"] is False
    mock_generate_meals.assert_not_called()


@pytest.mark.asyncio
async def test_call_tool_runs_an_allowed_tool_and_records_the_event(mock_generate_meals):
    mock_generate_meals.return_value = {"meals": make_meals(500, count=4), "withinTolerance": True}
    events = []
    payload = MealGeneratorInput(targets={"totalCalories": 2000, "macros": {}}, prefs=VALID_PREFS)
    result = await call_tool(MealGeneratorAgent(), "generate_meals", payload, events, step=3, wf_id="abc", allowed=["generate_meals"])
    assert result["ok"] is True and len(result["data"]["meals"]) == 4
    assert events[0]["tool"] == "generate_meals" and events[0]["ok"] is True and "duration_ms" in events[0]


@pytest.mark.asyncio
async def test_call_tool_turns_a_timeout_into_a_clean_failure(monkeypatch):
    import asyncio
    import src.agent.workflow as workflow

    class Slow:
        name = "NutritionAnalystAgent"

        async def run(self, payload):
            await asyncio.sleep(5)

    monkeypatch.setattr(workflow, "_DEFAULT_TOOL_TIMEOUT_SECONDS", 0.05)
    events = []
    result = await call_tool(Slow(), "calculate_targets", NutritionAnalystInput(prefs=VALID_PREFS), events, step=1)
    assert result["ok"] is False and "timed out" in result["error"]
    assert events[0]["ok"] is False


def test_new_workflow_records_the_route_and_a_planner_event(client, auth_headers, mock_generate_meals):
    from conftest import generate_and_wait, new_user_id
    headers = auth_headers(user_id=new_user_id())
    workflow_id, detail = generate_and_wait(client, headers, HIGH_RISK_PREFS, mock_generate_meals)
    assert detail["route"] == "medical_review"
    trace = client.get(f"/api/diet/workflows/{workflow_id}/trace", headers=headers).json()
    assert trace["events"][0]["agent"] == "planner" and trace["events"][0]["route"] == "medical_review"
    reviewer = client.get(f"/api/diet/workflows/{workflow_id}", headers=auth_headers(user_id=1, role="Admin")).json()
    assert expected_target_calories(HIGH_RISK_PREFS) == reviewer["targets"]["totalCalories"]
