# BackendAPI/GymAgentService/fitness_agent/api/fitness_routes.py
import uuid
import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db import get_session
from fitness_agent.schemas.fitness import FitnessProfileInput
from fitness_agent.schemas.progress import ProgressRecord
from fitness_agent.schemas.approval import ApprovalRequest, ApprovalResult
from fitness_agent.schemas.workflow import FitnessWorkflowResult
from fitness_agent.state import FitnessWorkflowState
from fitness_agent.graph import FitnessWorkflowGraph
from fitness_agent.tools.exercise_tool import search_exercises, APPROVED_EXERCISE_CATALOG
from fitness_agent.tools.workout_tool import save_workout_plan, log_tool_execution
from fitness_agent.models_fitness import (
    FitnessProfile,
    WorkoutPlanEntity,
    FitnessAgentWorkflow,
    FitnessAgentApproval
)

router = APIRouter(prefix="/api/fitness-agent", tags=["Fitness Agent"])
workflow_engine = FitnessWorkflowGraph()


@router.post("/workflows", response_model=FitnessWorkflowResult)
async def start_fitness_workflow(
    profile: FitnessProfileInput,
    session: Session = Depends(get_session)
):
    """
    Internal endpoint: Initiates multi-agent fitness planning workflow.
    """
    workflow_id = f"wf-{uuid.uuid4().hex[:8]}"
    initial_state = FitnessWorkflowState(
        workflow_id=workflow_id,
        user_id=profile.user_id or 1,
        profile=profile
    )

    final_state = await workflow_engine.execute(initial_state)

    # Persist state
    try:
        wf_entity = FitnessAgentWorkflow(
            workflow_id=workflow_id,
            user_id=profile.user_id or 1,
            objective=f"Adaptive Workout for {profile.fitness_goal}",
            current_step=final_state.current_step,
            status=final_state.status,
            state_data=final_state.model_dump()
        )
        session.add(wf_entity)
        session.commit()

        if final_state.generated_plan:
            save_workout_plan(final_state.generated_plan, session)
    except Exception as e:
        session.rollback()
        print(f"Error persisting workflow state: {e}")

    return workflow_engine.to_result(final_state)


@router.post("/workflows/{workflow_id}/progress", response_model=FitnessWorkflowResult)
async def generate_adaptive_schedule(
    workflow_id: str,
    record: ProgressRecord,
    profile: FitnessProfileInput,
    session: Session = Depends(get_session)
):
    """
    Internal endpoint: Generates next week's schedule adapted from logged progress.
    """
    new_workflow_id = f"wf-prog-{uuid.uuid4().hex[:8]}"
    initial_state = FitnessWorkflowState(
        workflow_id=new_workflow_id,
        user_id=record.user_id or 1,
        profile=profile,
        progress_record=record
    )

    final_state = await workflow_engine.execute(initial_state)

    try:
        if final_state.generated_plan:
            save_workout_plan(final_state.generated_plan, session)
    except Exception as e:
        print(f"Error saving progress plan: {e}")

    return workflow_engine.to_result(final_state)


@router.get("/workflows/{workflow_id}")
def get_workflow_details(workflow_id: str, session: Session = Depends(get_session)):
    """
    Internal endpoint: Retrieves workflow state & audit execution trail.
    """
    wf = session.query(FitnessAgentWorkflow).filter(FitnessAgentWorkflow.workflow_id == workflow_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf.state_data


@router.post("/workflows/{workflow_id}/approve", response_model=ApprovalResult)
def submit_plan_approval(
    workflow_id: str,
    req: ApprovalRequest,
    session: Session = Depends(get_session)
):
    """
    Internal endpoint: Records authorized human approval/rejection decision.
    """
    plan = session.query(WorkoutPlanEntity).filter(WorkoutPlanEntity.workflow_id == workflow_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Workout plan not found for workflow")

    status_mapping = {
        "APPROVE": "APPROVED",
        "REJECT": "REJECTED",
        "REQUEST_REVISION": "REVISION_REQUIRED"
    }

    new_status = status_mapping.get(req.decision.value, "PENDING")
    plan.status = new_status

    approval_record = FitnessAgentApproval(
        workflow_id=workflow_id,
        approver_id=req.approver_id,
        decision=req.decision.value,
        reason=req.reason
    )
    session.add(approval_record)
    session.commit()

    return ApprovalResult(
        workflow_id=workflow_id,
        status=new_status,
        decision=req.decision,
        approver_id=req.approver_id,
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
    )


@router.get("/exercises")
def get_catalog_exercises(muscle: str = None, difficulty: str = None):
    """
    Internal endpoint: Queries allow-listed exercise catalog.
    """
    return search_exercises(target_muscle=muscle, difficulty=difficulty)
