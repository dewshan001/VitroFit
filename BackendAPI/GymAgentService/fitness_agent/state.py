# BackendAPI/GymAgentService/fitness_agent/state.py
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from fitness_agent.schemas.fitness import FitnessProfileInput, SafetyScreeningResult
from fitness_agent.schemas.workout import WorkoutPlan
from fitness_agent.schemas.progress import ProgressRecord, ProgressAnalysis
from fitness_agent.schemas.workflow import ValidationResult, ToolCallRecord


class FitnessWorkflowState(BaseModel):
    workflow_id: str
    user_id: Optional[int] = 1
    profile: FitnessProfileInput
    screening_result: Optional[SafetyScreeningResult] = None
    progress_record: Optional[ProgressRecord] = None
    progress_analysis: Optional[ProgressAnalysis] = None
    generated_plan: Optional[WorkoutPlan] = None
    validation_result: Optional[ValidationResult] = None
    approval_status: str = "PENDING"
    approval_decision: Optional[str] = None
    approver_id: Optional[int] = None
    retry_count: int = 0
    current_step: str = "INTAKE"
    status: str = "RUNNING"  # RUNNING, AWAITING_APPROVAL, APPROVED, REJECTED, SAFE_FAILURE, COMPLETED
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    error: Optional[Dict[str, Any]] = None
