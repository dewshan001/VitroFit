# BackendAPI/GymAgentService/fitness_agent/schemas/workflow.py
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from fitness_agent.schemas.fitness import FitnessProfileInput, SafetyScreeningResult
from fitness_agent.schemas.workout import WorkoutPlan
from fitness_agent.schemas.progress import ProgressAnalysis


class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    checked_rules: List[str] = Field(default_factory=list)


class ToolCallRecord(BaseModel):
    tool_name: str
    inputs: Dict[str, Any]
    outputs: Any
    timestamp: str


class FitnessWorkflowResult(BaseModel):
    success: bool
    workflow_id: str
    status: str
    plan: Optional[WorkoutPlan] = None
    screening_result: Optional[SafetyScreeningResult] = None
    progress_analysis: Optional[ProgressAnalysis] = None
    validation_result: Optional[ValidationResult] = None
    error: Optional[Dict[str, Any]] = None
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    message: Optional[str] = None
