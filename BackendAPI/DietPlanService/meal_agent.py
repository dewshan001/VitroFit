# DietPlanService/meal_agent.py
"""Builds the meal-generation prompt and calls Gemini. The LLM only fills in
food items - it never computes the calorie/macro targets themselves
(calculator.py is the source of truth for those). Output is validated against
the targets before being returned; anything that can't be parsed into valid
JSON, or that fails even after a retry, surfaces as a clean error instead of
raising - main.py turns that into a 502, never a 500.
"""
import os
import json
import re
import asyncio
from openai import AsyncOpenAI
from dotenv import load_dotenv

from budget_reference import resolve_tier

load_dotenv()

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
PRIMARY_MODEL = os.getenv("NVIDIA_MODEL_PRIMARY", "meta/llama-3.2-11b-vision-instruct")
FALLBACK_MODEL = os.getenv("NVIDIA_MODEL_FALLBACK", "meta/llama-3.2-11b-vision-instruct")

if not NVIDIA_API_KEY:
    print("WARNING: NVIDIA_API_KEY is missing! Set it in your .env file.")

client = AsyncOpenAI(api_key=NVIDIA_API_KEY, base_url="https://integrate.api.nvidia.com/v1")

_CALL_TIMEOUT_SECONDS = 40
_TOLERANCE = 0.10  # +/-10%

_SYSTEM_INSTRUCTION = (
    "You are a nutrition-planning assistant for a gym app. Given a user's calorie/macro "
    "targets and preferences, produce a full day's meal plan that fits those targets. "
    "Respond with ONLY a single JSON object, no prose, no markdown fences, no thinking process. "
    'Shape: {"meals": [{"type": "breakfast", "label": "Breakfast", "items": '
    '[{"name": "...", "portion": "...", "calories": 000, "macros": {"protein": 0, "carbs": 0, "fat": 0}}]}]}. '
    "Every meal's items must sum toward the given daily calorie/macro targets as closely as possible. "
    "Respect all dietary restrictions, dislikes, and medical conditions absolutely - never include a "
    "restricted or disliked ingredient. Only suggest ingredients plausible at the given budget tier, "
    "using the reference price list as a guide to what's affordable. Match suggestions to the user's "
    "cooking time/skill level (e.g. no-cook or very quick items only if they indicated limited time)."
)


def _build_prompt(targets: dict, prefs: dict) -> str:
    tier = resolve_tier(prefs.get("budgetTier", "medium"), prefs.get("budgetCustomAmount"))
    return json.dumps({
        "dailyTargets": targets,
        "mealFrequency": prefs.get("mealFrequency"),
        "restrictions": prefs.get("restrictions", []),
        "dislikes": prefs.get("dislikes", ""),
        "medicalConditions": prefs.get("medicalConditions", []),
        "cookingTime": prefs.get("cookingTime"),
        "budget": {
            "tier": tier["label"],
            "guidance": tier["guidance"],
            "referencePricesLkr": tier["reference_items"],
        },
    }, ensure_ascii=False)


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


async def _call_model(model_id: str, prompt: str) -> str:
    response = await asyncio.wait_for(
        client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": _SYSTEM_INSTRUCTION},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1500,
            temperature=0.6,
        ),
        timeout=_CALL_TIMEOUT_SECONDS,
    )
    return response.choices[0].message.content or ""


async def generate_meals(targets: dict, prefs: dict) -> dict:
    """Returns either {"meals": [...], "withinTolerance": bool} on success, or
    {"error": "..."} on failure - callers must check for "error" rather than
    assuming success.
    """
    prompt = _build_prompt(targets, prefs)

    raw = None
    for model_id in (PRIMARY_MODEL, FALLBACK_MODEL):
        try:
            raw = await _call_model(model_id, prompt)
            if raw:
                break
        except Exception as e:
            print(f"DietPlanService: model '{model_id}' call failed: {e}")
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
            raw_retry = await _call_model(PRIMARY_MODEL, corrective_prompt)
            retry_parsed = _parse_llm_json(raw_retry)
        except Exception as e:
            print(f"DietPlanService: tolerance-correction retry failed: {e}")
            retry_parsed = None

        if retry_parsed is not None:
            retry_totals = _sum_totals(retry_parsed["meals"])
            if _within_tolerance(retry_totals, targets):
                return {"meals": retry_parsed["meals"], "withinTolerance": True}
            meals = retry_parsed["meals"]

        return {"meals": meals, "withinTolerance": False}

    return {"meals": meals, "withinTolerance": True}
