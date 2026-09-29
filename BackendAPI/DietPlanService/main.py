# DietPlanService/main.py
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import FastAPI, Depends, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from db import Base, engine, get_session
from models import DietPlanInputs, DietPlan
from auth import get_current_user_id, get_current_user_claims
from security import require_roles, _extract_role
import workflow_models  # noqa: F401 - registers DietWorkflow with Base before create_all
from workflow_models import DietWorkflow
from workflow import create_workflow, execute_workflow, execute_refine
from validators import validate_plan

# Holds strong references to in-flight background workflow tasks so asyncio
# doesn't garbage-collect them mid-run (a bare asyncio.create_task() result
# that nothing holds onto can be silently dropped).
_background_tasks: set[asyncio.Task] = set()

load_dotenv()

Base.metadata.create_all(bind=engine)

GenderLiteral = Literal["male", "female", "other"]
ActivityLevelLiteral = Literal["sedentary", "light", "moderate", "active"]
GoalLiteral = Literal["weight loss", "muscle gain", "maintenance", "endurance"]
MealFrequencyLiteral = Literal["3Meals", "4Meals", "5Meals", "intermittent"]
RestrictionLiteral = Literal[
    "vegetarian", "vegan", "halal", "dairy-free", "gluten-free",
    "peanut allergy", "lactose-intolerant",
]
MedicalConditionLiteral = Literal[
    "diabetes", "high blood pressure", "high cholesterol",
    "heart condition", "kidney condition", "thyroid condition",
]
BudgetTierLiteral = Literal["low", "medium", "high", "custom"]
CookingTimeLiteral = Literal["quick", "moderate", "nocook"]

app = FastAPI(
    title="VitroFit Diet Plan Agent API",
    description="Personalised nutrition plans: deterministic calorie/macro targets + LLM-generated meals.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _sanitize_free_text(v: str | None, max_len: int) -> str | None:
    """Strips control characters and caps length on any free-text field sent
    to the LLM (dislikes, refine instructions) - keeps user text well-formed
    data, never something that could be used to pad/break the JSON prompt.
    """
    if not v:
        return v
    cleaned = "".join(c for c in v if c.isprintable() or c in " \n")
    return cleaned[:max_len]


class DietPlanPreferences(BaseModel):
    age: int = Field(..., ge=10, le=100)
    gender: GenderLiteral
    heightCm: float = Field(..., ge=100, le=260)
    weightKg: float = Field(..., ge=30, le=250)
    activityLevel: ActivityLevelLiteral
    goal: GoalLiteral
    mealFrequency: MealFrequencyLiteral
    restrictions: list[RestrictionLiteral] = []
    dislikes: str | None = ""
    budgetTier: BudgetTierLiteral
    budgetCustomAmount: float | None = Field(default=None, ge=500, le=15000)
    medicalConditions: list[MedicalConditionLiteral] = []
    cookingTime: CookingTimeLiteral

    @field_validator("dislikes")
    @classmethod
    def _sanitize_dislikes(cls, v: str | None) -> str | None:
        return _sanitize_free_text(v, max_len=500)


class ConfirmPlanRequest(BaseModel):
    inputs: DietPlanPreferences
    totalCalories: int
    macros: dict
    meals: list
    withinTolerance: bool = True
    workflowId: str | None = None


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "VitroFit Diet Plan Agent"}


def _violations_to_message(violations: list[dict]) -> str:
    """The frontend (VitroFit_web/src/api/dietPlan.js) reads error responses as
    `data?.detail` and passes it straight to `new Error(...)`, which requires a
    string - an object detail stringifies to "[object Object]". Violations are
    still returned in full via the /workflows/{id} and /trace endpoints for
    anyone who wants the structured detail; this is just the human-readable
    summary for the immediate error message.
    """
    if not violations:
        return (
            "We couldn't generate a plan that's safe for your preferences. "
            "Please review your restrictions and medical conditions, or adjust your calorie target, and try again."
        )
    messages = [v.get("message", v.get("code", "")) for v in violations if v.get("severity") == "reject"] or [
        v.get("message", v.get("code", "")) for v in violations
    ]
    detail = "; ".join(m for m in messages if m)
    return (
        "We couldn't generate a plan that's safe for your preferences. "
        f"Specifically: {detail}. Please adjust your restrictions, medical conditions, or budget and try again."
    )


@app.post("/api/diet/generate")
async def generate_plan(
    prefs: DietPlanPreferences,
    user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_session),
):
    """Starts the workflow and returns the workflowId immediately - it does
    NOT wait for the LLM. The actual run happens in a detached background
    task (execute_workflow) so the frontend can poll
    GET /api/diet/workflows/{id} and show each agent's real progress live
    instead of the request blocking for up to _OVERALL_TIME_BUDGET_SECONDS.
    """
    wf = create_workflow(
        objective="generate_diet_plan",
        prefs=prefs.model_dump(),
        user_id=user_id,
        session=session,
    )
    task = asyncio.create_task(execute_workflow(wf.id, prefs.model_dump()))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return {
        "workflowId": str(wf.id),
        "status": wf.status,
        "plan": wf.plan,
    }


def _inputs_to_prefs(inputs: DietPlanInputs) -> dict:
    return {
        "age": inputs.age,
        "gender": inputs.gender,
        "heightCm": inputs.height_cm,
        "weightKg": inputs.weight_kg,
        "activityLevel": inputs.activity_level,
        "goal": inputs.goal,
        "mealFrequency": inputs.meal_frequency,
        "restrictions": inputs.restrictions,
        "dislikes": inputs.dislikes,
        "budgetTier": inputs.budget_tier,
        "budgetCustomAmount": inputs.budget_custom_amount,
        "medicalConditions": inputs.medical_conditions,
        "cookingTime": inputs.cooking_time,
    }


def _get_owned_plan(plan_id: int, user_id: int, session: Session) -> DietPlan:
    plan_row = session.get(DietPlan, plan_id)
    if not plan_row or plan_row.user_id != user_id:
        raise HTTPException(status_code=404, detail="Diet plan not found.")
    return plan_row


@app.get("/api/diet/plans")
def list_plans(
    user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_session),
):
    plans = (
        session.query(DietPlan)
        .filter(DietPlan.user_id == user_id)
        .order_by(DietPlan.created_at.desc())
        .all()
    )
    result = []
    for p in plans:
        inputs_row = session.get(DietPlanInputs, p.inputs_id)
        result.append({
            "id": p.id,
            "createdAt": p.created_at.isoformat(),
            "totalCalories": p.total_calories,
            "macros": p.macros,
            "meals": p.meals,
            "withinTolerance": p.within_tolerance,
            "inputs": _inputs_to_prefs(inputs_row) if inputs_row else None,
        })
    return result


@app.post("/api/diet/confirm")
def confirm_plan(
    req: ConfirmPlanRequest,
    user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_session),
):
    wf = None
    if req.workflowId:
        wf = session.get(DietWorkflow, uuid.UUID(req.workflowId))
        if not wf or wf.user_id != user_id:
            raise HTTPException(status_code=404, detail="Workflow not found.")
        if wf.status != "completed":
            raise HTTPException(status_code=409, detail=f"Workflow is not completed (status={wf.status}).")
        # Trust the workflow's own stored, validated data - ignore whatever
        # the client sent for these fields.
        req.totalCalories = wf.targets["totalCalories"]
        req.macros = wf.targets["macros"]
        req.meals = wf.meals
        req.withinTolerance = wf.validation_results.get("verdict") == "pass"
    else:
        # Legacy path (old frontend, no workflowId): validate the submitted
        # plan with the same deterministic rules before accepting it.
        result = validate_plan(req.meals, {"totalCalories": req.totalCalories, "macros": req.macros}, req.inputs.model_dump())
        if result["verdict"] == "reject":
            raise HTTPException(status_code=422, detail=_violations_to_message(result["violations"]))

    inputs_row = DietPlanInputs(
        user_id=user_id,
        age=req.inputs.age,
        gender=req.inputs.gender,
        height_cm=req.inputs.heightCm,
        weight_kg=req.inputs.weightKg,
        activity_level=req.inputs.activityLevel,
        goal=req.inputs.goal,
        meal_frequency=req.inputs.mealFrequency,
        restrictions=req.inputs.restrictions,
        dislikes=req.inputs.dislikes,
        budget_tier=req.inputs.budgetTier,
        budget_custom_amount=req.inputs.budgetCustomAmount,
        medical_conditions=req.inputs.medicalConditions,
        cooking_time=req.inputs.cookingTime,
    )
    session.add(inputs_row)
    session.flush()  # assigns inputs_row.id without committing yet

    plan_row = DietPlan(
        user_id=user_id,
        inputs_id=inputs_row.id,
        total_calories=req.totalCalories,
        macros=req.macros,
        meals=req.meals,
        within_tolerance=req.withinTolerance,
    )
    session.add(plan_row)
    session.commit()
    session.refresh(plan_row)

    if wf is not None:
        wf.plan_id = plan_row.id
        session.commit()

    return {"id": plan_row.id, "createdAt": plan_row.created_at.isoformat()}


@app.put("/api/diet/plans/{plan_id}")
def update_plan(
    plan_id: int,
    req: ConfirmPlanRequest,
    user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_session),
):
    plan_row = _get_owned_plan(plan_id, user_id, session)
    inputs_row = session.get(DietPlanInputs, plan_row.inputs_id)
    if not inputs_row:
        raise HTTPException(status_code=404, detail="Diet plan not found.")

    inputs_row.age = req.inputs.age
    inputs_row.gender = req.inputs.gender
    inputs_row.height_cm = req.inputs.heightCm
    inputs_row.weight_kg = req.inputs.weightKg
    inputs_row.activity_level = req.inputs.activityLevel
    inputs_row.goal = req.inputs.goal
    inputs_row.meal_frequency = req.inputs.mealFrequency
    inputs_row.restrictions = req.inputs.restrictions
    inputs_row.dislikes = req.inputs.dislikes
    inputs_row.budget_tier = req.inputs.budgetTier
    inputs_row.budget_custom_amount = req.inputs.budgetCustomAmount
    inputs_row.medical_conditions = req.inputs.medicalConditions
    inputs_row.cooking_time = req.inputs.cookingTime

    plan_row.total_calories = req.totalCalories
    plan_row.macros = req.macros
    plan_row.meals = req.meals
    plan_row.within_tolerance = req.withinTolerance

    session.commit()
    session.refresh(plan_row)

    return {"id": plan_row.id, "createdAt": plan_row.created_at.isoformat()}


@app.delete("/api/diet/plans/{plan_id}", status_code=204)
def delete_plan(
    plan_id: int,
    user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_session),
):
    plan_row = _get_owned_plan(plan_id, user_id, session)
    inputs_row = session.get(DietPlanInputs, plan_row.inputs_id)

    session.delete(plan_row)
    if inputs_row:
        session.delete(inputs_row)
    session.commit()

    return Response(status_code=204)


def _get_workflow_or_404(workflow_id: str, session: Session) -> DietWorkflow:
    try:
        parsed_id = uuid.UUID(workflow_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    wf = session.get(DietWorkflow, parsed_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    return wf


def _workflow_summary(wf: DietWorkflow) -> dict:
    return {
        "id": str(wf.id),
        "userId": wf.user_id,
        "status": wf.status,
        "riskLevel": wf.risk_level,
        "approvalStatus": wf.approval_status,
        "createdAt": wf.created_at.isoformat() if wf.created_at else None,
    }


def _workflow_message(wf: DietWorkflow) -> str | None:
    """Customer-facing summary for a terminal workflow, used by the frontend
    when polling GET /workflows/{id} - same idea as _violations_to_message()
    used for the (now-legacy, immediate) error paths elsewhere in this file.
    """
    if wf.status == "rejected":
        return _violations_to_message((wf.final_outcome or {}).get("violations", []))
    if wf.status == "failed":
        return wf.error or "Something went wrong while generating your plan. Please try again."
    if wf.status == "completed" and wf.error:
        # A requested edit (execute_refine) couldn't be applied - the plan
        # itself is still fine (kept unchanged), this is just a heads-up on
        # why the specific change didn't go through.
        return wf.error
    return None


def _workflow_detail(wf: DietWorkflow) -> dict:
    return {
        **_workflow_summary(wf),
        "objective": wf.objective,
        "plan": wf.plan,
        "completedSteps": wf.completed_steps,
        "targets": wf.targets,
        "meals": wf.meals,
        "validationResults": wf.validation_results,
        "finalOutcome": wf.final_outcome,
        "error": wf.error,
        "message": _workflow_message(wf),
        "retryCount": wf.retry_count,
        "approvedBy": wf.approved_by,
        "approvalNote": wf.approval_note,
        "planId": wf.plan_id,
    }


@app.get("/api/diet/approvals/pending")
def list_pending_approvals(
    claims: dict = Depends(require_roles("Trainer", "Admin")),
    session: Session = Depends(get_session),
):
    rows = (
        session.query(DietWorkflow)
        .filter(DietWorkflow.approval_status == "pending")
        .order_by(DietWorkflow.created_at.desc())
        .all()
    )
    return [_workflow_summary(r) for r in rows]


@app.post("/api/diet/workflows/{workflow_id}/approve")
def approve_workflow(
    workflow_id: str,
    note: str | None = None,
    claims: dict = Depends(require_roles("Trainer", "Admin")),
    session: Session = Depends(get_session),
):
    wf = _get_workflow_or_404(workflow_id, session)
    wf.approval_status = "approved"
    wf.approved_by = int(claims["sub"])
    wf.approval_note = note
    events = list(wf.events or [])
    events.append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "step": None, "agent": "approval", "tool": "approve",
        "ok": True, "error": None, "note": note, "approvedBy": wf.approved_by,
    })
    wf.events = events
    session.commit()
    return {"id": str(wf.id), "approvalStatus": wf.approval_status}


@app.post("/api/diet/workflows/{workflow_id}/reject")
def reject_workflow(
    workflow_id: str,
    note: str,
    claims: dict = Depends(require_roles("Trainer", "Admin")),
    session: Session = Depends(get_session),
):
    wf = _get_workflow_or_404(workflow_id, session)
    wf.approval_status = "rejected"
    wf.approved_by = int(claims["sub"])
    wf.approval_note = note
    events = list(wf.events or [])
    events.append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "step": None, "agent": "approval", "tool": "reject",
        "ok": True, "error": None, "note": note, "approvedBy": wf.approved_by,
    })
    wf.events = events
    session.commit()
    return {"id": str(wf.id), "approvalStatus": wf.approval_status}


def _require_owner_or_trainer_admin(wf: DietWorkflow, claims: dict) -> None:
    user_id = int(claims["sub"])
    if wf.user_id == user_id:
        return
    if _extract_role(claims) in ("Trainer", "Admin"):
        return
    raise HTTPException(status_code=403, detail="Not authorized to view this workflow.")


@app.get("/api/diet/workflows/{workflow_id}")
def get_workflow(
    workflow_id: str,
    claims: dict = Depends(get_current_user_claims),
    session: Session = Depends(get_session),
):
    wf = _get_workflow_or_404(workflow_id, session)
    _require_owner_or_trainer_admin(wf, claims)
    return _workflow_detail(wf)


@app.get("/api/diet/workflows/{workflow_id}/trace")
def get_workflow_trace(
    workflow_id: str,
    claims: dict = Depends(get_current_user_claims),
    session: Session = Depends(get_session),
):
    wf = _get_workflow_or_404(workflow_id, session)
    _require_owner_or_trainer_admin(wf, claims)
    return {
        "id": str(wf.id),
        "plan": wf.plan,
        "completedSteps": wf.completed_steps,
        "events": wf.events,
        "retryCount": wf.retry_count,
    }


class RefinePlanRequest(BaseModel):
    instruction: str = Field(..., min_length=1)

    @field_validator("instruction")
    @classmethod
    def _sanitize_instruction(cls, v: str) -> str:
        cleaned = _sanitize_free_text(v, max_len=300)
        if not cleaned or not cleaned.strip():
            raise ValueError("instruction cannot be empty.")
        return cleaned


@app.post("/api/diet/workflows/{workflow_id}/refine")
async def refine_plan(
    workflow_id: str,
    req: RefinePlanRequest,
    user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_session),
):
    """Applies one free-text edit (e.g. "swap the rice at lunch for
    something else") to an already-generated plan, instead of the user
    having to go back through the whole preferences form. Same start-now,
    poll-for-progress pattern as /generate: returns immediately, runs in the
    background, poll GET /workflows/{id} for the result.
    """
    wf = _get_workflow_or_404(workflow_id, session)
    if wf.user_id != user_id:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    if wf.status != "completed":
        raise HTTPException(status_code=409, detail=f"This plan isn't ready to edit yet (status={wf.status}).")

    wf.status = "running"
    session.commit()

    task = asyncio.create_task(execute_refine(wf.id, req.instruction))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return {"workflowId": str(wf.id), "status": wf.status}
