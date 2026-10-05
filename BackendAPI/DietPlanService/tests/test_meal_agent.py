# DietPlanService/tests/test_meal_agent.py
import json

from src.prompts.agent_prompts import build_prompt as _build_prompt, build_refine_prompt as _build_refine_prompt


def test_build_prompt_omits_feedback_by_default():
    prompt = _build_prompt({"totalCalories": 2000, "macros": {}}, {"mealFrequency": "3Meals"})
    assert "previousAttemptFeedback" not in json.loads(prompt)


def test_build_prompt_includes_corrective_note_when_present():
    prefs = {"mealFrequency": "3Meals", "_corrective_note": "Previous attempt was 34% under target."}
    prompt = _build_prompt({"totalCalories": 2000, "macros": {}}, prefs)
    payload = json.loads(prompt)
    assert payload["previousAttemptFeedback"] == "Previous attempt was 34% under target."


def test_build_refine_prompt_carries_current_plan_and_instruction():
    current_meals = [{"type": "lunch", "label": "Lunch", "items": [{"name": "Rice", "portion": "1 cup", "calories": 200, "macros": {"protein": 4, "carbs": 45, "fat": 1}}]}]
    prompt = _build_refine_prompt(
        {"totalCalories": 2000, "macros": {}},
        {"restrictions": ["vegetarian"], "dislikes": ""},
        current_meals,
        "instead of rice in lunch, include something else",
    )
    payload = json.loads(prompt)
    assert payload["currentPlan"]["meals"] == current_meals
    assert payload["userRequestedChange"] == "instead of rice in lunch, include something else"
    assert payload["restrictions"] == ["vegetarian"]
