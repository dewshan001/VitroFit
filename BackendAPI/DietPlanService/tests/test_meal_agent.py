# DietPlanService/tests/test_meal_agent.py
import json

from meal_agent import _build_prompt


def test_build_prompt_omits_feedback_by_default():
    prompt = _build_prompt({"totalCalories": 2000, "macros": {}}, {"mealFrequency": "3Meals"})
    assert "previousAttemptFeedback" not in json.loads(prompt)


def test_build_prompt_includes_corrective_note_when_present():
    prefs = {"mealFrequency": "3Meals", "_corrective_note": "Previous attempt was 34% under target."}
    prompt = _build_prompt({"totalCalories": 2000, "macros": {}}, prefs)
    payload = json.loads(prompt)
    assert payload["previousAttemptFeedback"] == "Previous attempt was 34% under target."
