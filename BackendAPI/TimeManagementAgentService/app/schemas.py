from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")

class TimeSlot(Contract):
    day: int = Field(ge=1, le=7)
    startTime: str
    endTime: str
    focus: str
    durationMinutes: int
    description: str = Field(default="", description="Comma-separated list of exercises or activities for this slot")

class Timetable(Contract):
    week: int
    slots: list[TimeSlot]

class GenerateRequest(Contract):
    workflowId: UUID
    runId: UUID
    plan: dict # The workout plan JSON
    profile: dict # User profile
    preferences: str = "" # e.g. "prefers mornings"

class GenerateResult(Contract):
    status: Literal["Ready", "ReviewRequired", "Failed"]
    timetable: Timetable | None = None
    longTermImpact: str = ""
    errors: list[str] = Field(default_factory=list)

class Trace(Contract):
    step: str
    summary: str
    durationMs: int = 0
    snapshot: dict = Field(default_factory=dict)
