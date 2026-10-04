# DietPlanService/agents.py
"""The three agents of the diet-plan workflow. Each has one job, a strict
Pydantic input/output contract, and an explicit allowed_tools list that
workflow.call_tool() enforces - an agent can never invoke a tool outside its
own list.

All three expose `async def run(...)` (including SafetyValidatorAgent, which
does no I/O) so workflow.py's dispatcher can `await agent.run(...)` uniformly
without a special-cased sync branch - negligible cost, simpler orchestrator.
"""
from typing import Literal
from pydantic import BaseModel

from calculator import calculate_targets
from budget_reference import resolve_tier
from meal_agent import generate_meals, refine_meals
from validators import validate_plan

_CALORIE_FLOOR = 1200
_STEEP_DEFICIT_RATIO = 0.25


class RiskFlag(BaseModel):
    code: str
    message: str


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


# ---------------------------------------------------------------------------
# Nutrition Analyst Agent - domain analysis
# ---------------------------------------------------------------------------

class NutritionAnalystInput(BaseModel):
    prefs: dict


class NutritionAnalystOutput(BaseModel):
    targets: dict
    risk_level: Literal["low", "medium", "high"]
    risk_flags: list[RiskFlag]
    budget_context: dict


class NutritionAnalystAgent:
    """Computes deterministic calorie/macro targets, assesses safety risk, and
    grounds the plan in budget-tier reference pricing. Never touches the LLM.
    """

    name = "NutritionAnalystAgent"
    allowed_tools = ["calculate_targets", "assess_risk", "lookup_budget"]

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


# ---------------------------------------------------------------------------
# Meal Generator Agent - action / tool use (LLM)
# ---------------------------------------------------------------------------

class MealGeneratorInput(BaseModel):
    targets: dict
    prefs: dict
    corrective_note: str | None = None
    # Set together to request a targeted edit to an existing plan (via the
    # refine_meals tool) instead of a fresh generation (generate_meals).
    current_meals: list[dict] | None = None
    instruction: str | None = None


class MealItem(BaseModel):
    name: str
    portion: str
    calories: float
    macros: dict


class Meal(BaseModel):
    type: str
    label: str
    items: list[MealItem]


class MealGeneratorOutput(BaseModel):
    meals: list[Meal]
    withinTolerance: bool
    error: str | None = None


class MealGeneratorAgent:
    """Generates (or, via refine_meals, targeted-edits) a day's meals through
    the existing NVIDIA NIM LLM call. Cannot touch the database, and cannot
    compute calories/macros - those come in already fixed via `targets`.
    """

    name = "MealGeneratorAgent"
    allowed_tools = ["generate_meals", "refine_meals"]

    async def run(self, input: MealGeneratorInput) -> MealGeneratorOutput:
        if input.current_meals is not None and input.instruction:
            result = await refine_meals(input.targets, input.prefs, input.current_meals, input.instruction)
        else:
            prefs = dict(input.prefs)
            if input.corrective_note:
                # meal_agent._build_prompt reads this key and surfaces it to
                # the LLM as previousAttemptFeedback, so a workflow-level
                # revise retry actually targets the Safety Validator's
                # specific violations instead of just repeating the same
                # prompt.
                prefs["_corrective_note"] = input.corrective_note
            result = await generate_meals(input.targets, prefs)

        if "error" in result:
            return MealGeneratorOutput(meals=[], withinTolerance=False, error=result["error"])

        return MealGeneratorOutput(meals=result["meals"], withinTolerance=result["withinTolerance"])


# ---------------------------------------------------------------------------
# Safety Validator Agent - validation / safety (no LLM)
# ---------------------------------------------------------------------------

class SafetyValidatorInput(BaseModel):
    meals: list[dict]
    targets: dict
    prefs: dict


class SafetyValidatorOutput(BaseModel):
    verdict: Literal["pass", "revise", "reject"]
    violations: list[dict]


class SafetyValidatorAgent:
    """Applies fixed rule-based checks to a generated plan. No AI, no tools
    beyond validate_plan.
    """

    name = "SafetyValidatorAgent"
    allowed_tools = ["validate_plan"]

    async def run(self, input: SafetyValidatorInput) -> SafetyValidatorOutput:
        result = validate_plan(input.meals, input.targets, input.prefs)
        return SafetyValidatorOutput(**result)
