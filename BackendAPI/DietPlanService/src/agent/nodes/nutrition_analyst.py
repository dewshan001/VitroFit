# DietPlanService/src/agent/nodes/nutrition_analyst.py
"""Nutrition Analyst Agent - domain analysis. Each agent has one job, a strict
Pydantic input/output contract (src/models/contracts.py) and an explicit
allowed_tools list that workflow.call_tool() enforces - an agent can never
invoke a tool outside its own list.

All three agents expose `async def run(...)` (including the Safety Validator,
which does no I/O) so workflow.py's dispatcher can `await agent.run(...)`
uniformly without a special-cased sync branch.
"""
from src.models.contracts import NutritionAnalystInput, NutritionAnalystOutput, RiskFlag
from src.tools.budget_reference import resolve_tier
from src.tools.calculator import calculate_targets
from src.tools.tool_registry import tools_for

_CALORIE_FLOOR = 1200
_STEEP_DEFICIT_RATIO = 0.25


def _assess_risk(prefs: dict, targets: dict) -> tuple[str, list[RiskFlag]]:
    """New logic (no existing equivalent): classifies a plan's risk level from
    age, medical conditions, and how steep a deficit the deterministic targets
    represent versus the same profile's maintenance calories. calculator.py
    remains the only source of calorie numbers - this only compares two of its
    outputs, it never invents its own calorie figure.
    """
    flags: list[RiskFlag] = []
    age = prefs.get("age", 0)
    medical = prefs.get("medicalConditions") or []
    calories = targets.get("totalCalories", 0)

    maintenance_targets = calculate_targets(
        gender=prefs.get("gender", "other"),
        age=age,
        height_cm=prefs.get("heightCm", 0),
        weight_kg=prefs.get("weightKg", 0),
        activity_level=prefs.get("activityLevel", "moderate"),
        goal="maintenance",
    )
    maintenance = maintenance_targets["totalCalories"]
    deficit_ratio = (maintenance - calories) / maintenance if maintenance > 0 else 0.0

    if age < 18:
        flags.append(RiskFlag(code="UNDER_18", message="User is under 18."))
    if medical:
        flags.append(RiskFlag(code="MEDICAL_CONDITIONS_PRESENT", message=f"{len(medical)} condition(s) declared."))
    if calories < _CALORIE_FLOOR:
        flags.append(RiskFlag(code="BELOW_SAFE_FLOOR", message=f"Target calories below the {_CALORIE_FLOOR} kcal safe floor."))
    if deficit_ratio >= _STEEP_DEFICIT_RATIO:
        flags.append(RiskFlag(code="STEEP_DEFICIT", message=f"Target is {deficit_ratio:.0%} below maintenance."))

    if calories < _CALORIE_FLOOR or (medical and age < 18):
        risk_level = "high"
    elif medical or deficit_ratio >= _STEEP_DEFICIT_RATIO or age < 18:
        risk_level = "medium"
    else:
        risk_level = "low"

    return risk_level, flags


class NutritionAnalystAgent:
    """Computes deterministic calorie/macro targets, assesses safety risk, and
    grounds the plan in budget-tier reference pricing. Never touches the LLM.
    """

    name = "NutritionAnalystAgent"
    allowed_tools = tools_for("NutritionAnalystAgent")

    async def run(self, input: NutritionAnalystInput) -> NutritionAnalystOutput:
        prefs = input.prefs
        targets = calculate_targets(
            gender=prefs.get("gender", "other"),
            age=prefs.get("age", 0),
            height_cm=prefs.get("heightCm", 0),
            weight_kg=prefs.get("weightKg", 0),
            activity_level=prefs.get("activityLevel", "moderate"),
            goal=prefs.get("goal", "maintenance"),
        )
        risk_level, risk_flags = _assess_risk(prefs, targets)
        budget_context = resolve_tier(prefs.get("budgetTier", "medium"), prefs.get("budgetCustomAmount"))

        return NutritionAnalystOutput(
            targets=targets,
            risk_level=risk_level,
            risk_flags=risk_flags,
            budget_context=budget_context,
        )
