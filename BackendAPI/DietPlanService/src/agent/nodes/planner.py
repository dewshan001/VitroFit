# DietPlanService/src/agent/nodes/planner.py
"""Planner - deterministic, no LLM, no tools. Turns the objective and the user's
preferences into the step list the coordinator runs, picks a route, and narrows
which tools this run may call. The step list shape is what the frontend renders
(step / agent / tool / description / status) and is unchanged.
"""
from src.models.contracts import PlanResult

# The refine flow is a separate request on a finished plan, so it is not one of
# the plan's steps; the coordinator adds it explicitly (see allowed_tools_for).
REFINE_TOOL = "refine_meals"


def choose_route(prefs: dict) -> str:
    """'medical_review' applies extra scrutiny (declared medical conditions or a
    minor); everything else follows the standard route."""
    if prefs.get("medicalConditions") or (prefs.get("age") or 99) < 18:
        return "medical_review"
    return "standard"


def build_plan(objective: str, prefs: dict) -> list[dict]:
    """Static, explainable 3-4 step plan - not dynamic re-planning. Adaptation
    is limited to a single note appended when medical conditions are present.
    """
    steps = [
        {"step": 1, "agent": "NutritionAnalystAgent", "tool": "calculate_targets",
         "description": "Compute calorie/macro targets and budget context.", "status": "pending"},
        {"step": 2, "agent": "NutritionAnalystAgent", "tool": "assess_risk",
         "description": "Assess health/safety risk level from age, medical conditions, deficit.", "status": "pending"},
        {"step": 3, "agent": "MealGeneratorAgent", "tool": "generate_meals",
         "description": "Generate a day's meals matching targets and preferences.", "status": "pending"},
        {"step": 4, "agent": "SafetyValidatorAgent", "tool": "validate_plan",
         "description": "Validate meals against targets, restrictions, and medical rules.", "status": "pending"},
    ]
    if prefs.get("medicalConditions"):
        steps[3]["description"] += " (medical_review: extra scrutiny applied due to declared medical conditions.)"
    return steps


def allowed_tools_for(plan: list[dict] | None, refine: bool = False) -> list[str] | None:
    """Tools this run may call: exactly those named in its plan (plus refine_meals for an edit).
    None means 'no plan recorded' (e.g. a row created before the planner existed) - role limits still apply."""
    if not plan:
        return None
    tools = [step["tool"] for step in plan if step.get("tool")]
    if refine:
        tools.append(REFINE_TOOL)
    return tools


def run(objective: str, prefs: dict) -> PlanResult:
    steps = build_plan(objective, prefs)
    return PlanResult(steps=steps, route=choose_route(prefs), allowed_tools=allowed_tools_for(steps) or [])
