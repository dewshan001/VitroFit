# DietPlanService/src/api/routes.py
"""All /api/diet endpoints (generate, workflow progress/trace, refine, confirm,
saved plans, Trainer/Admin approvals). Mounted by src/api/app.py."""
import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import update
from sqlalchemy.orm import Session

from src.utils.db import get_session
from src.models.db_models import DietPlanInputs, DietPlan, DietWorkflow
from src.models.schemas import DietPlanPreferences, ConfirmPlanRequest, RefinePlanRequest
from src.utils.auth import get_current_user_id, get_current_user_claims
from src.utils.security import require_roles, require_service_key, _extract_role
from src.agent.workflow import create_workflow, execute_workflow, execute_refine
from src.utils.validators import validate_plan
from src.tools.calculator import calculate_targets
from src.agent.nodes.nutrition_analyst import _assess_risk
from src.utils.injection_guard import guard_field
from src.utils.logger import log_event
from src.utils.pending_plans import approve_pending_plan, discard_pending_plan

# Holds strong references to in-flight background workflow tasks so asyncio
# doesn't garbage-collect them mid-run (a bare asyncio.create_task() result
# that nothing holds onto can be silently dropped).
_background_tasks: set[asyncio.Task] = set()

router = APIRouter(prefix="/api/diet", dependencies=[Depends(require_service_key)])


def _guard_free_text(value: str | None, label: str, limit: int) -> tuple[str, list[str]]:
    """Runs a user-typed free-text field through the injection guard. Returns the
    normalised text and any signal codes; refuses the request (422, plain string
    `detail` like every other error here) when the text reads like an instruction
    to the AI rather than a description of foods."""
    guarded = guard_field(value, source=label, limit=limit)
    if guarded.blocked:
        raise HTTPException(
            status_code=422,
            detail=f"Your {label} contains text that looks like an instruction to the AI. "
                   "Please describe it in plain words (for example, the foods you want to avoid).",
        )
    return guarded.text, guarded.flags


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


@router.post("/generate")
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
    prefs.dislikes, guard_flags = _guard_free_text(prefs.dislikes, "dislikes note", 500)
    wf = create_workflow(
        objective="generate_diet_plan",
        prefs=prefs.model_dump(),
        user_id=user_id,
        session=session,
        guard_flags=guard_flags,
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


@router.get("/plans")
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
        if p.approval_status == "pending":
            # Awaiting specialist review: the customer only learns that it exists.
            result.append({"id": p.id, "createdAt": p.created_at.isoformat(), "approvalStatus": "pending"})
            continue
        inputs_row = session.get(DietPlanInputs, p.inputs_id)
        result.append({
            "approvalStatus": "approved",
            "id": p.id,
            "createdAt": p.created_at.isoformat(),
            "totalCalories": p.total_calories,
            "macros": p.macros,
            "meals": p.meals,
            "withinTolerance": p.within_tolerance,
            "inputs": _inputs_to_prefs(inputs_row) if inputs_row else None,
        })
    return result


def _approval_block_message(wf: DietWorkflow) -> str | None:
    """Why a plan cannot be saved yet, or None. Only high-risk plans ever carry a
    pending/rejected approval, so low/medium-risk users are never affected."""
    if wf.approval_status == "pending":
        return (
            "This plan needs Trainer/Admin approval before it can be saved. "
            "Please ask a Trainer or Admin to review it, then try saving again."
        )
    if wf.approval_status == "rejected":
        note = f" Reason: {wf.approval_note}" if wf.approval_note else ""
        return f"A Trainer/Admin declined this plan, so it can't be saved.{note} Please generate a new plan."
    return None


def _resolve_plan_to_save(req: ConfirmPlanRequest, user_id: int, session: Session):
    """Shared by POST /confirm and PUT /plans/{id}: decides what exactly gets
    saved and whether it may be saved at all. Returns (workflow_or_None, totalCalories,
    macros, meals, withinTolerance).

    With a workflowId the workflow's own stored, validated data is used (whatever
    the client sent for the plan is ignored) and its approval state is enforced.
    Without one (old clients) the submitted plan is checked with the same
    deterministic rules against targets recomputed on the server, and a plan that
    would need approval cannot be saved because nothing links it to a review.
    """
    req.inputs.dislikes, _ = _guard_free_text(req.inputs.dislikes, "dislikes note", 500)

    if req.workflowId:
        try:
            workflow_id = uuid.UUID(req.workflowId)
        except ValueError:
            raise HTTPException(status_code=404, detail="Workflow not found.")
        wf = session.get(DietWorkflow, workflow_id)
        if not wf or wf.user_id != user_id:
            raise HTTPException(status_code=404, detail="Workflow not found.")
        if wf.status != "completed":
            raise HTTPException(status_code=409, detail=f"Workflow is not completed (status={wf.status}).")
        blocked = _approval_block_message(wf)
        if blocked:
            raise HTTPException(status_code=409, detail=blocked)
        # Trust the workflow's own stored, validated data - ignore whatever
        # the client sent for these fields.
        return (
            wf,
            wf.targets["totalCalories"],
            wf.targets["macros"],
            wf.meals,
            wf.validation_results.get("verdict") == "pass",
        )

    # Legacy path (old frontend, no workflowId).
    prefs = req.inputs.model_dump()
    targets = calculate_targets(
        gender=prefs["gender"], age=prefs["age"], height_cm=prefs["heightCm"],
        weight_kg=prefs["weightKg"], activity_level=prefs["activityLevel"], goal=prefs["goal"],
    )
    risk_level, _flags = _assess_risk(prefs, targets)
    if risk_level == "high":
        raise HTTPException(
            status_code=409,
            detail="This plan needs Trainer/Admin approval before it can be saved. "
                   "Please generate it again so it can be reviewed, then save it.",
        )
    result = validate_plan(req.meals, targets, prefs)
    if result["verdict"] == "reject":
        raise HTTPException(status_code=422, detail=_violations_to_message(result["violations"]))
    return None, targets["totalCalories"], targets["macros"], req.meals, req.withinTolerance


def _apply_plan_update(plan_row, inputs_row, req: ConfirmPlanRequest, total_calories, macros, meals, within_tolerance) -> None:
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

    plan_row.total_calories = total_calories
    plan_row.macros = macros
    plan_row.meals = meals
    plan_row.within_tolerance = within_tolerance


@router.post("/confirm")
def confirm_plan(
    req: ConfirmPlanRequest,
    user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_session),
):
    wf, total_calories, macros, meals, within_tolerance = _resolve_plan_to_save(req, user_id, session)

    # A high-risk plan was already saved (as pending) at generation time and made
    # visible by the approval: saving it now updates that row instead of adding a copy.
    if wf is not None and wf.risk_level == "high" and wf.plan_id:
        existing = session.get(DietPlan, wf.plan_id)
        existing_inputs = session.get(DietPlanInputs, existing.inputs_id) if existing else None
        if existing and existing_inputs and existing.user_id == user_id:
            _apply_plan_update(existing, existing_inputs, req, total_calories, macros, meals, within_tolerance)
            session.commit()
            session.refresh(existing)
            return {"id": existing.id, "createdAt": existing.created_at.isoformat()}

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
        total_calories=total_calories,
        macros=macros,
        meals=meals,
        within_tolerance=within_tolerance,
    )
    session.add(plan_row)
    session.commit()
    session.refresh(plan_row)

    if wf is not None:
        wf.plan_id = plan_row.id
        session.commit()

    return {"id": plan_row.id, "createdAt": plan_row.created_at.isoformat()}


@router.put("/plans/{plan_id}")
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
    if plan_row.approval_status == "pending":
        raise HTTPException(status_code=409, detail="This plan is awaiting specialist review and can't be edited yet.")

    # Same checks as /confirm: an update used to store whatever meals the client
    # sent, unvalidated and ungated.
    wf, total_calories, macros, meals, within_tolerance = _resolve_plan_to_save(req, user_id, session)

    _apply_plan_update(plan_row, inputs_row, req, total_calories, macros, meals, within_tolerance)

    session.commit()
    session.refresh(plan_row)

    if wf is not None:
        wf.plan_id = plan_row.id
        session.commit()

    return {"id": plan_row.id, "createdAt": plan_row.created_at.isoformat()}


@router.delete("/plans/{plan_id}", status_code=204)
def delete_plan(
    plan_id: int,
    user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_session),
):
    plan_row = _get_owned_plan(plan_id, user_id, session)
    inputs_row = session.get(DietPlanInputs, plan_row.inputs_id)

    if plan_row.approval_status == "pending":
        # Withdrawing a plan that is still under review takes it out of the reviewers' queue too.
        waiting = (
            session.query(DietWorkflow)
            .filter(DietWorkflow.plan_id == plan_row.id, DietWorkflow.approval_status == "pending")
            .all()
        )
        for wf in waiting:
            wf.approval_status = "rejected"
            wf.approval_note = "Withdrawn by the customer."
            wf.decided_at = datetime.now(timezone.utc)
            wf.plan_id = None

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


def _risk_flags(wf: DietWorkflow) -> list:
    for step in wf.completed_steps or []:
        if step.get("riskFlags") is not None:
            return step["riskFlags"]
    return []


def _workflow_detail(wf: DietWorkflow, hide_content: bool = False) -> dict:
    """`hide_content` withholds the generated plan (targets, meals, validation,
    outcome) - used when the customer asks about their own plan that is still
    awaiting specialist review."""
    return {
        **_workflow_summary(wf),
        "objective": wf.objective,
        "plan": wf.plan,
        "completedSteps": wf.completed_steps,
        "inputs": wf.inputs,
        "riskFlags": _risk_flags(wf),
        "targets": None if hide_content else wf.targets,
        "meals": None if hide_content else wf.meals,
        "validationResults": None if hide_content else wf.validation_results,
        "finalOutcome": None if hide_content else wf.final_outcome,
        "error": wf.error,
        "message": _workflow_message(wf),
        "retryCount": wf.retry_count,
        "approvedBy": wf.approved_by,
        "approvalNote": wf.approval_note,
        "approverRole": wf.approver_role,
        "decidedAt": wf.decided_at.isoformat() if wf.decided_at else None,
        "route": wf.route,
        "planId": wf.plan_id,
    }


@router.get("/approvals/pending")
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
    return [
        {
            **_workflow_summary(r),
            "riskFlags": _risk_flags(r),
            "totalCalories": (r.targets or {}).get("totalCalories"),
        }
        for r in rows
    ]


def _decide(workflow_id: str, decision: str, note: str | None, claims: dict, session: Session) -> dict:
    """Records a Trainer/Admin decision. Only a plan that is waiting for review
    (`pending`) can be decided, exactly once: the status change is a single
    conditional UPDATE, so two reviewers (or a double click) cannot both win."""
    wf = _get_workflow_or_404(workflow_id, session)
    if wf.status != "completed" or wf.approval_status != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"This plan isn't waiting for review (approval status: {wf.approval_status or 'none'}).",
        )
    new_status = "approved" if decision == "approve" else "rejected"
    approver_id = int(claims["sub"])
    note = (note or "").strip()[:1000] or None
    claimed = session.execute(
        update(DietWorkflow)
        .where(DietWorkflow.id == wf.id, DietWorkflow.approval_status == "pending")
        .values(
            approval_status=new_status, approved_by=approver_id, approver_role=_extract_role(claims),
            approval_note=note, decided_at=datetime.now(timezone.utc),
        )
    ).rowcount
    if not claimed:
        session.rollback()
        raise HTTPException(status_code=409, detail="Another reviewer has already decided this plan.")
    session.refresh(wf)
    events = list(wf.events or [])
    events.append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "step": None, "agent": "approval", "tool": decision,
        "ok": True, "error": None, "note": note, "approvedBy": approver_id,
        "approverRole": wf.approver_role,
    })
    wf.events = events
    if decision == "approve":
        approve_pending_plan(session, wf)  # the customer's saved plan becomes visible
    else:
        discard_pending_plan(session, wf)  # a declined plan disappears from the customer's list
    session.commit()
    log_event("approval decided", wf.id, decision=decision, approver_role=wf.approver_role)
    return {"id": str(wf.id), "approvalStatus": wf.approval_status}


@router.post("/workflows/{workflow_id}/approve")
def approve_workflow(
    workflow_id: str,
    note: str | None = None,
    claims: dict = Depends(require_roles("Trainer", "Admin")),
    session: Session = Depends(get_session),
):
    return _decide(workflow_id, "approve", note, claims, session)


@router.post("/workflows/{workflow_id}/reject")
def reject_workflow(
    workflow_id: str,
    note: str,
    claims: dict = Depends(require_roles("Trainer", "Admin")),
    session: Session = Depends(get_session),
):
    return _decide(workflow_id, "reject", note, claims, session)


def _require_owner_or_trainer_admin(wf: DietWorkflow, claims: dict) -> None:
    user_id = int(claims["sub"])
    if wf.user_id == user_id:
        return
    if _extract_role(claims) in ("Trainer", "Admin"):
        return
    raise HTTPException(status_code=403, detail="Not authorized to view this workflow.")


@router.get("/workflows/{workflow_id}")
def get_workflow(
    workflow_id: str,
    claims: dict = Depends(get_current_user_claims),
    session: Session = Depends(get_session),
):
    wf = _get_workflow_or_404(workflow_id, session)
    _require_owner_or_trainer_admin(wf, claims)
    hide = wf.user_id == int(claims["sub"]) and wf.approval_status == "pending"
    return _workflow_detail(wf, hide_content=hide)


@router.get("/workflows/{workflow_id}/trace")
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


@router.post("/workflows/{workflow_id}/refine")
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

    instruction, guard_flags = _guard_free_text(req.instruction, "edit request", 300)

    wf.status = "running"
    if guard_flags:
        # Codes only, never the text (monitor mode lets it through but records it).
        wf.events = list(wf.events or []) + [{
            "ts": datetime.now(timezone.utc).isoformat(), "step": None, "agent": "guard",
            "tool": "scan_instruction", "ok": True, "error": None, "guard_flags": guard_flags,
        }]
    session.commit()

    task = asyncio.create_task(execute_refine(wf.id, instruction))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return {"workflowId": str(wf.id), "status": wf.status}
