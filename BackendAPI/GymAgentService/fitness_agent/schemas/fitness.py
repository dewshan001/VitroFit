# BackendAPI/GymAgentService/fitness_agent/schemas/fitness.py
from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class FitnessGoal(str, Enum):
    MUSCLE_GAIN = "Muscle Gain & Strength"
    FAT_LOSS = "Fat Loss & Conditioning"
    GENERAL_HEALTH = "General Health & Posture"
    ENDURANCE = "Athletic Endurance"


class ExperienceLevel(str, Enum):
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"


class HealthInformation(BaseModel):
    conditions: List[str] = Field(default_factory=list)
    injuries: Optional[str] = None
    medications: Optional[str] = None
    cleared_by_physician: bool = True


class FitnessProfileInput(BaseModel):
    user_id: Optional[int] = None
    age: int = Field(..., ge=14, le=100)
    height_cm: float = Field(..., ge=80, le=260)
    weight_kg: float = Field(..., ge=30, le=300)
    fitness_goal: FitnessGoal = FitnessGoal.GENERAL_HEALTH
    experience_level: ExperienceLevel = ExperienceLevel.BEGINNER
    available_days: List[str] = Field(default=["Monday", "Wednesday", "Friday"])
    session_duration: int = Field(45, ge=20, le=120)
    selected_gym: Optional[str] = None
    health_information: HealthInformation = Field(default_factory=HealthInformation)
    image_metadata: Optional[dict] = None


class SafetyScreeningResult(BaseModel):
    status: str = Field(..., description="'SAFE' | 'REVIEW_REQUIRED'")
    risk_flags: List[str] = Field(default_factory=list)
    reason: str
    recommended_action: str = Field(..., description="'CONTINUE' | 'CONTACT_PROFESSIONAL'")
