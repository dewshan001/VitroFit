# BackendAPI/GymAgentService/fitness_agent/schemas/workout.py
from typing import List, Optional
from pydantic import BaseModel, Field


class Exercise(BaseModel):
    id: str
    name: str
    target_muscle: str
    difficulty: str
    equipment: str
    beginner_allowed: bool = True
    instructions: str
    safety_notes: Optional[str] = None


class WorkoutExercise(BaseModel):
    id: str
    name: str
    target_muscle: str
    sets: int = Field(..., ge=1, le=8)
    reps: str = Field(..., description="e.g. '8-12' or '10'")
    rest: str = Field(..., description="e.g. '60s' or '90s'")
    duration_minutes: Optional[int] = None
    equipment: str
    instructions: str
    safety_notes: Optional[str] = None


class WorkoutDay(BaseModel):
    day: str = Field(..., description="e.g. Monday, Wednesday, Friday")
    focus: str = Field(..., description="e.g. Full Body Foundations")
    duration_minutes: int = Field(45, ge=20, le=120)
    exercises: List[WorkoutExercise] = Field(default_factory=list)


class WorkoutPlan(BaseModel):
    workflow_id: str
    user_id: Optional[int] = None
    week: int = Field(1, ge=1, le=52)
    title: str
    status: str = "AWAITING_APPROVAL"  # AWAITING_APPROVAL, APPROVED, REJECTED, REVISION_REQUIRED
    target_experience: str
    session_duration_minutes: int = 45
    days: List[WorkoutDay] = Field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
