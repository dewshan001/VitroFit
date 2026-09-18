# BackendAPI/GymAgentService/fitness_agent/agents/coordinator.py
from typing import Dict, Any
from fitness_agent.schemas.fitness import FitnessProfileInput


class CoordinatorAgent:
    """
    Agent 1: Fitness Intake / Coordinator Agent.
    Validates completeness of incoming profile, sets execution strategy,
    and initializes structured workflow state.
    """

    def process_intake(self, profile: FitnessProfileInput) -> Dict[str, Any]:
        errors = []
        if profile.age < 14 or profile.age > 100:
            errors.append(f"Age {profile.age} is outside eligible range (14-100).")
        if profile.weight_kg < 30:
            errors.append("Valid weight (kg) is required.")
        if profile.height_cm < 80:
            errors.append("Valid height (cm) is required.")
        if not profile.available_days:
            errors.append("At least one available workout day must be selected.")

        if errors:
            return {
                "status": "VALIDATION_FAILED",
                "errors": errors,
                "plan_required": False
            }

        return {
            "status": "INTAKE_COMPLETED",
            "objective": f"{profile.fitness_goal.value if hasattr(profile.fitness_goal, 'value') else profile.fitness_goal} for {profile.experience_level.value if hasattr(profile.experience_level, 'value') else profile.experience_level}",
            "days_count": len(profile.available_days),
            "session_duration": profile.session_duration,
            "plan_required": True
        }
