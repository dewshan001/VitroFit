# DietPlanService/calculator.py
"""Deterministic calorie/macro target math - the source of truth for numbers.
Ported from the frontend's mock generateMockPlan() in
VitroFit_web/src/components/DietPlan/DietPlan.jsx so v1 behaviour matches what
was already prototyped there. The LLM never computes calories - it only fills
in food items that should add up to these targets.
"""

ACTIVITY_FACTORS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
}

# Approx macro split (grams per 100 kcal), keyed by goal - same values as the
# frontend mock's MACRO_SPLIT table.
MACRO_SPLIT = {
    "weight loss": {"p": 12, "c": 9, "f": 3},
    "muscle gain": {"p": 14, "c": 11, "f": 3},
    "maintenance": {"p": 11, "c": 13, "f": 3},
    "endurance": {"p": 11, "c": 15, "f": 3},
}

_GOAL_MULTIPLIERS = {
    "weight loss": 0.85,
    "muscle gain": 1.12,
    "endurance": 1.05,
}


def calculate_targets(gender: str, age: int, height_cm: float, weight_kg: float,
                       activity_level: str, goal: str) -> dict:
    """Mifflin-St Jeor BMR * activity factor * goal multiplier, then a macro
    split derived from the goal. Returns {"totalCalories": int, "macros": {...}}.
    """
    if gender == "female":
        base = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
    else:
        base = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5

    factor = ACTIVITY_FACTORS.get(activity_level, 1.55)
    target = base * factor

    multiplier = _GOAL_MULTIPLIERS.get(goal)
    if multiplier:
        target *= multiplier

    total_calories = round(target)
    return {
        "totalCalories": total_calories,
        "macros": split_macros(total_calories, goal),
    }


def split_macros(total_calories: int, goal: str) -> dict:
    split = MACRO_SPLIT.get(goal, MACRO_SPLIT["maintenance"])
    return {
        "protein": round((split["p"] / 100) * total_calories),
        "carbs": round((split["c"] / 100) * total_calories),
        "fat": round((split["f"] / 100) * total_calories),
    }
