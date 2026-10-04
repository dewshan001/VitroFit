# DietPlanService/src/tools/tools.py
"""The Meal Generator Agent's two LLM-backed tools: generate_meals and
refine_meals. The LLM only fills in food items - it never computes the
calorie/macro targets themselves (calculator.py is the source of truth for
those). Output is validated against the targets before being returned;
anything that can't be parsed into valid JSON, or that fails even after a
retry, surfaces as a clean {"error": ...} instead of raising - the workflow
turns that into a failed run, never a 500.
"""
import json
import logging
import re

from src.models.llm_client import call_model, PRIMARY_MODEL, FALLBACK_MODEL
from src.prompts.agent_prompts import build_prompt, build_refine_prompt
from src.prompts.system_prompts import REFINE_SYSTEM_INSTRUCTION
from src.utils.logger import log_event

_TOLERANCE = 0.10  # +/-10%

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_llm_json(raw: str) -> dict | None:
    cleaned = (raw or "").replace("```json", "").replace("```", "").strip()
    match = _JSON_BLOCK_RE.search(cleaned)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except Exception:
        return None
    if not isinstance(data, dict) or not isinstance(data.get("meals"), list) or not data["meals"]:
        return None
    return data


def _sum_totals(meals: list) -> dict:
    totals = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
    for meal in meals:
        for item in meal.get("items", []):
            totals["calories"] += item.get("calories", 0) or 0
            macros = item.get("macros", {}) or {}
            totals["protein"] += macros.get("protein", 0) or 0
            totals["carbs"] += macros.get("carbs", 0) or 0
            totals["fat"] += macros.get("fat", 0) or 0
    return totals


def _within_tolerance(totals: dict, targets: dict) -> bool:
    target_kcal = targets["totalCalories"]
    if target_kcal <= 0:
        return True
    diff = abs(totals["calories"] - target_kcal) / target_kcal
    return diff <= _TOLERANCE


async def generate_meals(targets: dict, prefs: dict) -> dict:
    """Returns either {"meals": [...], "withinTolerance": bool} on success, or
    {"error": "..."} on failure - callers must check for "error" rather than
    assuming success.
    """
    prompt = build_prompt(targets, prefs)

    raw = None
    for model_id in (PRIMARY_MODEL, FALLBACK_MODEL):
        try:
            raw = await call_model(model_id, prompt)
            if raw:
                break
        except Exception as e:
            log_event("llm call failed", level=logging.WARNING, tool="generate_meals", model=model_id, error=type(e).__name__)
            raw = None
            continue

    if not raw:
        return {"error": "The meal-planning service is temporarily unavailable. Please try again."}

    parsed = _parse_llm_json(raw)
    if parsed is None:
        return {"error": "The meal-planning service returned an unreadable response. Please try again."}

    meals = parsed["meals"]
    totals = _sum_totals(meals)

    if not _within_tolerance(totals, targets):
        corrective_prompt = prompt + (
            f"\n\nYour previous attempt totalled approximately {totals['calories']} kcal, "
            f"but the target is {targets['totalCalories']} kcal. Adjust portion sizes so the "
            "total is much closer to the target."
        )
        try:
            raw_retry = await call_model(PRIMARY_MODEL, corrective_prompt)
            retry_parsed = _parse_llm_json(raw_retry)
        except Exception as e:
            log_event("llm call failed", level=logging.WARNING, tool="generate_meals", model=PRIMARY_MODEL, retry="tolerance", error=type(e).__name__)
            retry_parsed = None

        if retry_parsed is not None:
            retry_totals = _sum_totals(retry_parsed["meals"])
            if _within_tolerance(retry_totals, targets):
                return {"meals": retry_parsed["meals"], "withinTolerance": True}
            meals = retry_parsed["meals"]

        return {"meals": meals, "withinTolerance": False}

    return {"meals": meals, "withinTolerance": True}


async def refine_meals(targets: dict, prefs: dict, current_meals: list, instruction: str) -> dict:
    """Applies one free-text edit request to an existing plan (e.g. "swap the
    rice at lunch for something else"), keeping everything else as close to
    unchanged as the targets allow. Same return contract as generate_meals():
    {"meals": [...], "withinTolerance": bool} on success, {"error": "..."} on
    failure. The caller (MealGeneratorAgent) still runs this through the
    Safety Validator afterward - that deterministic check, not the prompt, is
    what actually guarantees an edit can't smuggle in a restricted ingredient
    even if the LLM doesn't follow the instructions.
    """
    prompt = build_refine_prompt(targets, prefs, current_meals, instruction)

    raw = None
    for model_id in (PRIMARY_MODEL, FALLBACK_MODEL):
        try:
            raw = await call_model(model_id, prompt, REFINE_SYSTEM_INSTRUCTION)
            if raw:
                break
        except Exception as e:
            log_event("llm call failed", level=logging.WARNING, tool="refine_meals", model=model_id, error=type(e).__name__)
            raw = None
            continue

    if not raw:
        return {"error": "The meal-planning service is temporarily unavailable. Please try again."}

    parsed = _parse_llm_json(raw)
    if parsed is None:
        return {"error": "The meal-planning service returned an unreadable response. Please try again."}

    meals = parsed["meals"]
    totals = _sum_totals(meals)
    return {"meals": meals, "withinTolerance": _within_tolerance(totals, targets)}
