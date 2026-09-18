# BackendAPI/GymAgentService/fitness_agent/tools/progress_tool.py
from typing import List, Optional
from sqlalchemy.orm import Session
from fitness_agent.models_fitness import ProgressRecordEntity, WorkoutPlanEntity
from fitness_agent.schemas.progress import ProgressRecord


def get_user_progress_history(user_id: int, session: Session = None) -> List[ProgressRecord]:
    """
    Allow-listed Progress History Tool.
    Retrieves previous progress submissions and adherence data for a given user.
    """
    if not session or not user_id:
        return []

    try:
        rows = (
            session.query(ProgressRecordEntity)
            .filter(ProgressRecordEntity.user_id == user_id)
            .order_by(ProgressRecordEntity.week_number.desc())
            .all()
        )
        return [
            ProgressRecord(
                user_id=r.user_id,
                week_number=r.week_number,
                completed_sessions=r.completed_sessions,
                target_sessions=r.target_sessions,
                weight_kg=r.weight_kg,
                rpe_rating=r.rpe_rating,
                performance_notes=r.performance_notes,
                exercise_performance=r.exercise_performance
            )
            for r in rows
        ]
    except Exception:
        return []


def get_latest_workout_plan(user_id: int, session: Session = None) -> Optional[dict]:
    """
    Allow-listed Tool to retrieve the user's latest workout plan.
    """
    if not session or not user_id:
        return None

    try:
        row = (
            session.query(WorkoutPlanEntity)
            .filter(WorkoutPlanEntity.user_id == user_id)
            .order_by(WorkoutPlanEntity.id.desc())
            .first()
        )
        if row:
            return {
                "workflow_id": row.workflow_id,
                "week": row.week_number,
                "title": row.title,
                "status": row.status,
                "plan_data": row.plan_data
            }
    except Exception:
        pass
    return None
