# DietPlanService/src/agent/nodes/meal_generator.py
"""Meal Generator Agent - action / tool use (LLM)."""
from src.models.contracts import MealGeneratorInput, MealGeneratorOutput
from src.tools.tool_registry import tools_for
from src.tools.tools import generate_meals, refine_meals


class MealGeneratorAgent:
    """Generates (or, via refine_meals, targeted-edits) a day's meals through
    the existing NVIDIA NIM LLM call. Cannot touch the database, and cannot
    compute calories/macros - those come in already fixed via `targets`.
    """

    name = "MealGeneratorAgent"
    allowed_tools = tools_for("MealGeneratorAgent")

    async def run(self, input: MealGeneratorInput) -> MealGeneratorOutput:
        if input.current_meals is not None and input.instruction:
            result = await refine_meals(input.targets, input.prefs, input.current_meals, input.instruction)
        else:
            prefs = dict(input.prefs)
            if input.corrective_note:
                # prompts.agent_prompts.build_prompt reads this key and surfaces it to
                # the LLM as previousAttemptFeedback, so a workflow-level
                # revise retry actually targets the Safety Validator's
                # specific violations instead of just repeating the same
                # prompt.
                prefs["_corrective_note"] = input.corrective_note
            result = await generate_meals(input.targets, prefs)

        if "error" in result:
            return MealGeneratorOutput(meals=[], withinTolerance=False, error=result["error"])

        return MealGeneratorOutput(meals=result["meals"], withinTolerance=result["withinTolerance"])
