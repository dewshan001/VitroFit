# DietPlanService/src/utils/pending_plans.py
"""A high-risk plan is saved for the customer as soon as it is generated, with
approval_status='pending', so it shows up in their plan list (without content)
while a Trainer/Admin reviews it. Approval makes it visible; rejection deletes it.
"""
from sqlalchemy.orm import Session

from src.models.db_models import DietPlan, DietPlanInputs, DietWorkflow


def _inputs_row_from_prefs(user_id: int, prefs: dict) -> DietPlanInputs:
    return DietPlanInputs(
        user_id=user_id,
        age=prefs.get("age"),
        gender=prefs.get("gender"),
        height_cm=prefs.get("heightCm"),
        weight_kg=prefs.get("weightKg"),
        activity_level=prefs.get("activityLevel"),
        goal=prefs.get("goal"),
        meal_frequency=prefs.get("mealFrequency"),
        restrictions=prefs.get("restrictions") or [],
        dislikes=prefs.get("dislikes"),
        budget_tier=prefs.get("budgetTier"),
        budget_custom_amount=prefs.get("budgetCustomAmount"),
        medical_conditions=prefs.get("medicalConditions") or [],
        cooking_time=prefs.get("cookingTime"),
    )


def sync_pending_plan(session: Session, wf: DietWorkflow) -> None:
    """Creates the pending plan row for a high-risk workflow, or - when one is
    already linked (e.g. the plan was edited) - refreshes it with the workflow's
    current meals and puts it back to pending. Commits."""
    if not wf.targets or not wf.meals:
        return
    within_tolerance = (wf.validation_results or {}).get("verdict") == "pass"
    plan = session.get(DietPlan, wf.plan_id) if wf.plan_id else None
    if plan is None:
        inputs_row = _inputs_row_from_prefs(wf.user_id, wf.inputs or {})
        session.add(inputs_row)
        session.flush()
        plan = DietPlan(user_id=wf.user_id, inputs_id=inputs_row.id, approval_status="pending")
        session.add(plan)
    plan.total_calories = wf.targets["totalCalories"]
    plan.macros = wf.targets["macros"]
    plan.meals = wf.meals
    plan.within_tolerance = within_tolerance
    plan.approval_status = "pending"
    session.flush()
    wf.plan_id = plan.id
    session.commit()


def approve_pending_plan(session: Session, wf: DietWorkflow) -> None:
    plan = session.get(DietPlan, wf.plan_id) if wf.plan_id else None
    if plan is not None:
        plan.approval_status = "approved"


def discard_pending_plan(session: Session, wf: DietWorkflow) -> None:
    """Deletes the plan (and its inputs) saved for this workflow. Does not commit."""
    plan = session.get(DietPlan, wf.plan_id) if wf.plan_id else None
    if plan is not None:
        inputs_row = session.get(DietPlanInputs, plan.inputs_id)
        session.delete(plan)
        if inputs_row is not None:
            session.flush()
            session.delete(inputs_row)
    wf.plan_id = None
