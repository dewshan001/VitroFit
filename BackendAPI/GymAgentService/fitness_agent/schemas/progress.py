# BackendAPI/GymAgentService/fitness_agent/schemas/progress.py
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class ProgressRecord(BaseModel):
    user_id: Optional[int] = None
    week_number: int = Field(..., ge=1)
    completed_sessions: int = Field(..., ge=0, le=7)
    target_sessions: int = Field(3, ge=1, le=7)
    weight_kg: float = Field(..., ge=30, le=300)
    rpe_rating: int = Field(..., ge=1, le=10, description="1 (very light) to 10 (maximum exertion)")
    performance_notes: Optional[str] = None
    exercise_performance: Optional[Dict[str, Any]] = None


class ProgressAnalysis(BaseModel):
    progress_status: str = Field(..., description="'PROGRESSING' | 'MAINTAINING' | 'FATIGUE_RECOVERY'")
    adherence_percentage: float = Field(..., ge=0, le=100)
    performance_summary: str
    recommended_adjustment: str
    next_plan_guidance: str
