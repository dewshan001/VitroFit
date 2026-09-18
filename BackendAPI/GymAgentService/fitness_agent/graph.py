# BackendAPI/GymAgentService/fitness_agent/graph.py
import datetime
from typing import Dict, Any, Optional

from fitness_agent.state import FitnessWorkflowState
from fitness_agent.config import MAX_AGENT_RETRIES
from fitness_agent.agents.coordinator import CoordinatorAgent
from fitness_agent.agents.safety_agent import SafetyScreeningAgent
from fitness_agent.agents.planner_agent import FitnessPlannerAgent
from fitness_agent.agents.progress_agent import ProgressAnalysisAgent
from fitness_agent.agents.validation_agent import FitnessValidationAgent
from fitness_agent.schemas.workflow import ToolCallRecord, FitnessWorkflowResult


class FitnessWorkflowGraph:
    """
    LangGraph-compatible Multi-Agent Orchestrator.
    Directs execution across Coordinator, Safety, Planner, Progress, and Validation agents.
    """

    def __init__(self):
        self.coordinator = CoordinatorAgent()
        self.safety_agent = SafetyScreeningAgent()
        self.planner = FitnessPlannerAgent()
        self.progress_agent = ProgressAnalysisAgent()
        self.validator = FitnessValidationAgent()

    async def execute(self, initial_state: FitnessWorkflowState) -> FitnessWorkflowState:
        state = initial_state
        state.status = "RUNNING"

        # Step 1: Coordinator / Intake
        state.current_step = "INTAKE"
        intake_res = self.coordinator.process_intake(state.profile)
        if intake_res["status"] == "VALIDATION_FAILED":
            state.status = "SAFE_FAILURE"
            state.error = {
                "code": "INVALID_INTAKE",
                "message": "; ".join(intake_res["errors"])
            }
            return state

        state.tool_calls.append(
            ToolCallRecord(
                tool_name="Coordinator Intake Validation",
                inputs={"profile": state.profile.model_dump(exclude={"health_information"})},
                outputs=intake_res,
                timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
            )
        )

        # Step 2: Health & Safety Screening
        state.current_step = "SAFETY_SCREENING"
        screening = self.safety_agent.screen_user(state.profile.health_information)
        state.screening_result = screening

        state.tool_calls.append(
            ToolCallRecord(
                tool_name="Safety Screening Guardrail",
                inputs={"health_conditions": state.profile.health_information.conditions},
                outputs=screening.model_dump(),
                timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
            )
        )

        if screening.status == "REVIEW_REQUIRED":
            state.status = "SAFE_FAILURE"
            state.error = {
                "code": "SAFETY_REVIEW_REQUIRED",
                "message": "The health screening agent detected declared conditions requiring professional clearance. An automated schedule cannot be generated safely at this time. Please consult a qualified healthcare provider."
            }
            return state

        # Step 3: Progress Analysis (if progressive adaptation workflow)
        if state.progress_record:
            state.current_step = "PROGRESS_ANALYSIS"
            analysis = self.progress_agent.analyze_progress(state.progress_record)
            state.progress_analysis = analysis
            state.tool_calls.append(
                ToolCallRecord(
                    tool_name="Progress Analysis Agent",
                    inputs=state.progress_record.model_dump(),
                    outputs=analysis.model_dump(),
                    timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
                )
            )

        # Step 4 & 5: Planning & Deterministic Validation Loop
        revision_feedback: Optional[str] = None
        week_num = state.progress_record.week_number + 1 if state.progress_record else 1

        while state.retry_count <= MAX_AGENT_RETRIES:
            state.current_step = "PLANNING"
            plan = await self.planner.generate_plan(
                workflow_id=state.workflow_id,
                profile=state.profile,
                progress_analysis=state.progress_analysis,
                week_number=week_num,
                revision_feedback=revision_feedback
            )
            state.generated_plan = plan

            state.current_step = "VALIDATION"
            val_result = self.validator.validate_plan(plan)
            state.validation_result = val_result

            state.tool_calls.append(
                ToolCallRecord(
                    tool_name="Deterministic Validation Agent",
                    inputs={"week": plan.week, "days": len(plan.days)},
                    outputs=val_result.model_dump(),
                    timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
                )
            )

            if val_result.is_valid:
                # Validated! Awaiting human approval
                state.status = "AWAITING_APPROVAL"
                state.current_step = "HUMAN_APPROVAL"
                return state

            # If invalid, record revision attempt
            state.retry_count += 1
            revision_feedback = "; ".join(val_result.errors)

        # Exceeded max retries without passing validation
        state.status = "SAFE_FAILURE"
        state.error = {
            "code": "VALIDATION_REVISION_EXCEEDED",
            "message": f"Generated plan failed deterministic safety rules after {MAX_AGENT_RETRIES} retries: {revision_feedback}"
        }
        return state

    def to_result(self, state: FitnessWorkflowState) -> FitnessWorkflowResult:
        return FitnessWorkflowResult(
            success=(state.status in ["AWAITING_APPROVAL", "APPROVED", "COMPLETED"]),
            workflow_id=state.workflow_id,
            status=state.status,
            plan=state.generated_plan,
            screening_result=state.screening_result,
            progress_analysis=state.progress_analysis,
            validation_result=state.validation_result,
            error=state.error,
            tool_calls=state.tool_calls,
            message="Plan generated, validated, and queued for trainer approval." if state.status == "AWAITING_APPROVAL" else None
        )
