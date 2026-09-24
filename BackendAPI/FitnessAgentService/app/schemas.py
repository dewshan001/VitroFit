"""Contracts shared with the ASP.NET fitness feature. Reject unexpected LLM fields."""
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Profile(Contract):
    age: int = Field(ge=18, le=80)
    heightCm: float = Field(ge=100, le=250)
    weightKg: float = Field(ge=30, le=300)
    goal: Literal["weight_loss", "muscle_building", "general_fitness", "strength", "endurance"]
    days: list[int] = Field(min_length=1, max_length=3)
    sessionMinutes: int = Field(ge=20, le=60)
    equipment: list[str] = Field(max_length=20)
    reviewRequired: bool

    @model_validator(mode="after")
    def unique_days(self):
        if len(set(self.days)) != len(self.days) or any(d < 1 or d > 7 for d in self.days):
            raise ValueError("Use unique ISO weekdays from 1 (Monday) to 7 (Sunday).")
        return self


class Exercise(Contract):
    id: int
    name: str
    equipment: str
    muscleGroup: str
    instructions: str
    beginnerAllowed: bool


class Prescription(Contract):
    exerciseId: int
    sets: int = Field(ge=1, le=3)
    repetitions: int = Field(ge=6, le=15)
    restSeconds: int = Field(ge=45, le=120)


class WorkoutDay(Contract):
    day: int = Field(ge=1, le=7)
    focus: Literal["Chest and triceps", "Arms and back", "Legs"]
    warmupMinutes: int = Field(ge=5, le=10)
    cooldownMinutes: int = Field(ge=5, le=10)
    exercises: list[Prescription] = Field(min_length=2, max_length=5)


class Plan(Contract):
    week: int = Field(ge=1, le=4)
    days: list[WorkoutDay] = Field(min_length=1, max_length=3)


class Progress(Contract):
    day: int = Field(ge=1, le=7)
    completed: bool
    rpe: int = Field(ge=1, le=10)
    pain: bool


class GenerateRequest(Contract):
    workflowId: UUID
    runId: UUID
    profile: Profile
    catalog: list[Exercise] = Field(min_length=1, max_length=100)
    previousPlan: Plan | None = None
    progress: list[Progress] = Field(default_factory=list, max_length=3)
    feedback: str = Field(default="", max_length=500)


class Trace(Contract):
    step: str
    summary: str
    durationMs: int = 0
    snapshot: dict = Field(default_factory=dict)


class GenerateResult(Contract):
    status: Literal["Ready", "ReviewRequired", "Failed"]
    plan: Plan | None = None
    errors: list[str] = Field(default_factory=list)
    analysis: str = ""
