# BackendAPI/GymAgentService/fitness_agent/tools/workout_tool.py
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from fitness_agent.models_fitness import (
    WorkoutPlanEntity,
    FitnessAgentWorkflow,
    FitnessAgentToolCall,
    FitnessAgentApproval
)
from fitness_agent.schemas.workout import WorkoutPlan


def save_workout_plan(plan: WorkoutPlan, session: Session = None) -> bool:
    """
    Allow-listed Persistence Tool: Save validated workout plan to database.
    """
    if not session:
        return True

    try:
        existing = session.query(WorkoutPlanEntity).filter(WorkoutPlanEntity.workflow_id == plan.workflow_id).first()
        if existing:
            existing.status = plan.status
            existing.plan_data = plan.model_dump()
        else:
            entity = WorkoutPlanEntity(
                workflow_id=plan.workflow_id,
                user_id=plan.user_id or 1,
                week_number=plan.week,
                title=plan.title,
                status=plan.status,
                target_experience=plan.target_experience,
                session_duration_minutes=plan.session_duration_minutes,
                plan_data=plan.model_dump()
            )
            session.add(entity)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        print(f"Error saving workout plan: {e}")
        return False


def log_tool_execution(
    workflow_id: str,
    tool_name: str,
    inputs: Dict[str, Any],
    outputs: Any,
    session: Session = None
) -> None:
    """
    Allow-listed Persistence Tool: Records auditable tool execution logs.
    """
    if not session or not workflow_id:
        return

    try:
        record = FitnessAgentToolCall(
            workflow_id=workflow_id,
            tool_name=tool_name,
            inputs=inputs,
            outputs=outputs if isinstance(outputs, (dict, list)) else {"result": str(outputs)}
        )
        session.add(record)
        session.commit()
    except Exception:
        session.rollback()
