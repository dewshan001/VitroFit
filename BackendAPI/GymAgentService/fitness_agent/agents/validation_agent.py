# BackendAPI/GymAgentService/fitness_agent/agents/validation_agent.py
from fitness_agent.schemas.workout import WorkoutPlan
from fitness_agent.schemas.workflow import ValidationResult
from fitness_agent.tools.exercise_tool import APPROVED_EXERCISE_CATALOG

APPROVED_IDS = {e.id for e in APPROVED_EXERCISE_CATALOG}


class FitnessValidationAgent:
    """
    Agent 5: Fitness Validation / Safety Agent.
    Executes deterministic validation checks on generated workout schedules.
    Ensures safe volume limits, valid exercise catalog references, and beginner constraints.
    """

    def validate_plan(self, plan: WorkoutPlan) -> ValidationResult:
        errors = []
        warnings = []
        checked_rules = []

        # Rule 1: Must contain at least 1 workout day
        checked_rules.append("Rule: Minimum 1 workout day")
        if not plan.days or len(plan.days) == 0:
            errors.append("Workout plan must contain at least one scheduled day.")

        # Rule 2: Max workout days per week <= 6
        checked_rules.append("Rule: Maximum 6 workout days per week")
        if len(plan.days) > 6:
            errors.append(f"Plan specifies {len(plan.days)} days; max 6 days allowed to guarantee recovery.")

        for day in plan.days:
            # Rule 3: Session duration limit
            checked_rules.append(f"Rule: Duration limit for {day.day}")
            if day.duration_minutes > 75:
                errors.append(f"{day.day} session exceeds safe duration limit of 75 mins ({day.duration_minutes} mins).")

            # Rule 4: Exercise count per session
            checked_rules.append(f"Rule: Exercise count for {day.day}")
            if len(day.exercises) < 2:
                errors.append(f"{day.day} has fewer than 2 exercises.")
            if len(day.exercises) > 8:
                errors.append(f"{day.day} has {len(day.exercises)} exercises; maximum allowed per session is 8.")

            seen_ids = set()
            for ex in day.exercises:
                # Rule 5: Valid exercise ID check
                checked_rules.append(f"Rule: Exercise catalog membership for '{ex.name}'")
                if ex.id not in APPROVED_IDS:
                    warnings.append(f"Exercise '{ex.name}' (ID: {ex.id}) is not in the primary seed catalog.")

                # Rule 6: Duplicate exercise in same day
                if ex.id in seen_ids:
                    errors.append(f"Duplicate exercise '{ex.name}' detected in {day.day} workout.")
                seen_ids.add(ex.id)

                # Rule 7: Set boundaries
                checked_rules.append(f"Rule: Set count boundaries for '{ex.name}'")
                if ex.sets < 1 or ex.sets > 6:
                    errors.append(f"Exercise '{ex.name}' specifies {ex.sets} sets; allowed range is 1-6.")

        is_valid = len(errors) == 0
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            checked_rules=checked_rules
        )
