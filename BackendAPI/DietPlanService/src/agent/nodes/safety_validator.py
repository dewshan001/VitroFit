# DietPlanService/src/agent/nodes/safety_validator.py
"""Safety Validator Agent - validation / safety (no LLM)."""
from src.models.contracts import SafetyValidatorInput, SafetyValidatorOutput
from src.tools.tool_registry import tools_for
from src.utils.validators import validate_plan


class SafetyValidatorAgent:
    """Applies fixed rule-based checks to a generated plan. No AI, no tools
    beyond validate_plan.
    """

    name = "SafetyValidatorAgent"
    allowed_tools = tools_for("SafetyValidatorAgent")

    async def run(self, input: SafetyValidatorInput) -> SafetyValidatorOutput:
        result = validate_plan(input.meals, input.targets, input.prefs)
        return SafetyValidatorOutput(**result)
