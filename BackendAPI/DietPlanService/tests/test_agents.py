# DietPlanService/tests/test_agents.py
import pytest

from src.agent.nodes.nutrition_analyst import _assess_risk, NutritionAnalystAgent
from src.agent.nodes.meal_generator import MealGeneratorAgent
from src.agent.nodes.safety_validator import SafetyValidatorAgent
from conftest import VALID_PREFS


def test_assess_risk_high_for_below_calorie_floor():
    prefs = dict(VALID_PREFS)
    targets = {"totalCalories": 1000}
    risk_level, flags = _assess_risk(prefs, targets)
    assert risk_level == "high"
    assert any(f.code == "BELOW_SAFE_FLOOR" for f in flags)


def test_assess_risk_low_for_healthy_adult():
    prefs = dict(VALID_PREFS, age=30, medicalConditions=[])
    targets = {"totalCalories": 2200}
    risk_level, flags = _assess_risk(prefs, targets)
    assert risk_level == "low"


@pytest.mark.asyncio
async def test_agent_tool_allowlists_are_scoped():
    assert NutritionAnalystAgent.allowed_tools == ["calculate_targets", "assess_risk", "lookup_budget"]
    assert MealGeneratorAgent.allowed_tools == ["generate_meals", "refine_meals"]
    assert SafetyValidatorAgent.allowed_tools == ["validate_plan"]
