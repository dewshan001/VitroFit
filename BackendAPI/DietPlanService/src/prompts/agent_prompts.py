# DietPlanService/src/prompts/agent_prompts.py
"""Builds the JSON user-message payloads sent to the LLM. All user-controlled
text travels as data inside this JSON, never concatenated into a system prompt."""
import json

from src.tools.budget_reference import resolve_tier
from src.utils.injection_guard import escape_for_fence


def _untrusted(value):
    """User-typed or model-derived text goes into the prompt as plain data: angle
    brackets are replaced so it can never write a tag that closes or fakes a fence."""
    return escape_for_fence(value) if isinstance(value, str) else value


def build_prompt(targets: dict, prefs: dict) -> str:
    tier = resolve_tier(prefs.get("budgetTier", "medium"), prefs.get("budgetCustomAmount"))
    payload = {
        "dailyTargets": targets,
        "mealFrequency": prefs.get("mealFrequency"),
        "restrictions": prefs.get("restrictions", []),
        "dislikes": _untrusted(prefs.get("dislikes", "")),
        "medicalConditions": prefs.get("medicalConditions", []),
        "cookingTime": prefs.get("cookingTime"),
        "budget": {
            "tier": tier["label"],
            "guidance": tier["guidance"],
            "referencePricesLkr": tier["reference_items"],
        },
    }
    # Set by workflow.py's revise loop when the Safety Validator returned
    # "revise" - specific violation feedback so this retry can actually
    # target what was wrong, not just repeat the same prompt.
    corrective_note = prefs.get("_corrective_note")
    if corrective_note:
        payload["previousAttemptFeedback"] = _untrusted(corrective_note)
    return json.dumps(payload, ensure_ascii=False)


def build_refine_prompt(targets: dict, prefs: dict, current_meals: list, instruction: str) -> str:
    tier = resolve_tier(prefs.get("budgetTier", "medium"), prefs.get("budgetCustomAmount"))
    return json.dumps({
        "dailyTargets": targets,
        "restrictions": prefs.get("restrictions", []),
        "dislikes": _untrusted(prefs.get("dislikes", "")),
        "medicalConditions": prefs.get("medicalConditions", []),
        "cookingTime": prefs.get("cookingTime"),
        "budget": {
            "tier": tier["label"],
            "guidance": tier["guidance"],
            "referencePricesLkr": tier["reference_items"],
        },
        "currentPlan": {"meals": current_meals},
        # Free-text description of what to change - always sent as data, never
        # concatenated into the system prompt; see REFINE_SYSTEM_INSTRUCTION
        # for why it can't override restrictions/dislikes/medical/targets.
        "userRequestedChange": _untrusted(instruction),
    }, ensure_ascii=False)
