# DietPlanService/validators.py
"""Deterministic, rule-based safety checks for a generated meal plan - no LLM
involved. This is the Safety Validator agent's only tool: validate_plan().

Keeps its own small tolerance check rather than importing meal_agent's private
_within_tolerance/_sum_totals, since those are internal to meal_agent's own
LLM self-correction retry and reaching into another module's underscore-
prefixed names would couple this file to those internals. The _TOLERANCE
constant here must be kept at 0.10 to match meal_agent.py's own constant.
"""

_TOLERANCE = 0.10  # +/-10%, keep in sync with meal_agent._TOLERANCE
# Beyond this, treat the miss as unfixable rather than worth a revise cycle.
# Raised from an initial 0.25 after real generations from the live model
# (meta/llama-3.2-11b-vision-instruct) came in 30%+ off target on a normal
# attempt - a value that low was rejecting plans outright instead of giving
# the revise loop (which now actually forwards feedback to the LLM, see
# meal_agent._build_prompt's previousAttemptFeedback) a chance to fix them.
_REJECT_TOLERANCE = 0.50

_CALORIE_FLOOR = 1200  # kcal/day, medically-oriented minimum
_MAX_ITEM_CALORIES = 1500
_MIN_MEALS = 1
_MAX_MEALS = 8
_MAX_PROTEIN_G = 400

# Keyword blocklists keyed by the exact restriction literals the frontend sends.
RESTRICTION_KEYWORDS = {
    "vegetarian": [
        "chicken", "beef", "pork", "fish", "shrimp", "prawn", "bacon", "ham",
        "meat", "mutton", "goat", "turkey", "salami", "sausage", "duck",
    ],
    "vegan": [
        "chicken", "beef", "pork", "fish", "shrimp", "prawn", "bacon", "ham",
        "meat", "mutton", "goat", "turkey", "salami", "sausage", "duck",
        "egg", "milk", "cheese", "yoghurt", "yogurt", "honey", "butter",
        "ghee", "curd", "cream",
    ],
    "halal": ["pork", "bacon", "ham", "alcohol", "wine", "beer"],
    "dairy-free": ["milk", "cheese", "yoghurt", "yogurt", "butter", "ghee", "curd", "cream"],
    "gluten-free": ["wheat", "bread", "pasta", "noodle", "flour", "barley", "rye", "roti", "naan"],
    "peanut allergy": ["peanut", "groundnut"],
    "lactose-intolerant": ["milk", "cheese", "yoghurt", "yogurt", "butter", "ghee", "curd", "cream"],
}

# Restrictions whose violation is a hard safety/religious issue -> reject.
# Softer preference mismatches (free-text dislikes) are revise-tier instead.
_REJECT_RESTRICTIONS = {"vegetarian", "vegan", "halal", "peanut allergy", "dairy-free", "lactose-intolerant", "gluten-free"}

_SUGAR_KEYWORDS = ["sugar", "honey", "syrup", "soda", "candy", "jaggery", "dessert"]
_SODIUM_KEYWORDS = ["pickle", "salted", "soy sauce", "processed", "canned", "instant noodle"]
_FRIED_FAT_KEYWORDS = ["fried", "deep-fried", "butter", "cream"]


def _violation(code: str, severity: str, message: str, field: str | None = None) -> dict:
    return {"code": code, "severity": severity, "message": message, "field": field}


def _check_schema(meals: list) -> list[dict]:
    if not isinstance(meals, list) or not meals:
        return [_violation("SCHEMA_INVALID", "reject", "Meals must be a non-empty list.")]

    violations = []
    for i, meal in enumerate(meals):
        if not isinstance(meal, dict):
            violations.append(_violation("SCHEMA_INVALID", "reject", f"Meal {i} is not an object.", f"meals[{i}]"))
            continue
        if not meal.get("type") or not meal.get("label"):
            violations.append(_violation("SCHEMA_INVALID", "reject", f"Meal {i} missing type/label.", f"meals[{i}]"))
        items = meal.get("items")
        if not isinstance(items, list) or not items:
            violations.append(_violation("SCHEMA_INVALID", "reject", f"Meal {i} has no items.", f"meals[{i}].items"))
            continue
        for j, item in enumerate(items):
            if not isinstance(item, dict) or not item.get("name"):
                violations.append(_violation("SCHEMA_INVALID", "reject", f"Meal {i} item {j} missing name.", f"meals[{i}].items[{j}]"))
                continue
            calories = item.get("calories")
            if not isinstance(calories, (int, float)) or calories < 0:
                violations.append(_violation("SCHEMA_INVALID", "reject", f"Meal {i} item {j} has invalid calories.", f"meals[{i}].items[{j}].calories"))
            macros = item.get("macros") or {}
            if not isinstance(macros, dict) or any(
                not isinstance(macros.get(k, 0), (int, float)) or macros.get(k, 0) < 0
                for k in ("protein", "carbs", "fat")
            ):
                violations.append(_violation("SCHEMA_INVALID", "reject", f"Meal {i} item {j} has invalid macros.", f"meals[{i}].items[{j}].macros"))
    return violations


def _sum_meal_totals(meals: list) -> dict:
    totals = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
    for meal in meals:
        for item in meal.get("items", []):
            totals["calories"] += item.get("calories", 0) or 0
            macros = item.get("macros", {}) or {}
            totals["protein"] += macros.get("protein", 0) or 0
            totals["carbs"] += macros.get("carbs", 0) or 0
            totals["fat"] += macros.get("fat", 0) or 0
    return totals


def _check_calorie_tolerance(totals: dict, targets: dict) -> list[dict]:
    target_kcal = targets.get("totalCalories", 0)
    if target_kcal <= 0:
        return []
    diff_ratio = abs(totals["calories"] - target_kcal) / target_kcal
    if diff_ratio <= _TOLERANCE:
        return []
    severity = "reject" if diff_ratio > _REJECT_TOLERANCE else "revise"
    return [_violation(
        "CALORIE_OUT_OF_TOLERANCE", severity,
        f"Total calories {totals['calories']:.0f} is {diff_ratio:.0%} off the {target_kcal} target.",
    )]


def _check_macro_sanity(totals: dict) -> list[dict]:
    violations = []
    if totals["protein"] > _MAX_PROTEIN_G:
        violations.append(_violation("MACRO_IMPLAUSIBLE", "revise", f"Protein {totals['protein']:.0f}g/day is implausibly high."))

    implied_kcal = totals["protein"] * 4 + totals["carbs"] * 4 + totals["fat"] * 9
    if totals["calories"] > 0 and implied_kcal > 0:
        diff_ratio = abs(implied_kcal - totals["calories"]) / totals["calories"]
        if diff_ratio > 0.15:
            violations.append(_violation(
                "MACRO_IMPLAUSIBLE", "revise",
                f"Macro grams imply {implied_kcal:.0f} kcal, {diff_ratio:.0%} off the summed item calories.",
            ))
    return violations


def _check_restrictions_and_dislikes(meals: list, prefs: dict) -> list[dict]:
    violations = []
    restrictions = prefs.get("restrictions") or []
    active_keywords = set()
    reject_keywords = set()
    for r in restrictions:
        keywords = RESTRICTION_KEYWORDS.get(r, [])
        active_keywords.update(keywords)
        if r in _REJECT_RESTRICTIONS:
            reject_keywords.update(keywords)

    dislikes = (prefs.get("dislikes") or "").lower()
    dislike_tokens = [t.strip() for t in dislikes.replace(",", " ").split() if len(t.strip()) >= 3]

    for i, meal in enumerate(meals):
        for j, item in enumerate(meal.get("items", [])):
            name = (item.get("name") or "").lower()
            for kw in active_keywords:
                if kw in name:
                    severity = "reject" if kw in reject_keywords else "revise"
                    violations.append(_violation(
                        "RESTRICTION_VIOLATION", severity,
                        f"'{item.get('name')}' conflicts with restriction keyword '{kw}'.",
                        f"meals[{i}].items[{j}]",
                    ))
            for tok in dislike_tokens:
                if tok in name:
                    violations.append(_violation(
                        "DISLIKE_MATCH", "revise",
                        f"'{item.get('name')}' matches disliked term '{tok}'.",
                        f"meals[{i}].items[{j}]",
                    ))
    return violations


def _check_medical_conditions(meals: list, targets: dict, prefs: dict) -> list[dict]:
    violations = []
    medical = prefs.get("medicalConditions") or []
    if not medical:
        return violations

    if targets.get("totalCalories", 0) < _CALORIE_FLOOR:
        violations.append(_violation(
            "BELOW_SAFE_FLOOR", "reject",
            f"Target {targets.get('totalCalories')} kcal is below the {_CALORIE_FLOOR} kcal safe floor "
            "with a medical condition declared.",
        ))

    keyword_checks = []
    if "diabetes" in medical:
        keyword_checks.append(("DIABETES_SUGAR_RISK", _SUGAR_KEYWORDS))
    if "high blood pressure" in medical or "kidney condition" in medical:
        keyword_checks.append(("SODIUM_RISK", _SODIUM_KEYWORDS))
    if "heart condition" in medical:
        keyword_checks.append(("FRIED_FAT_RISK", _FRIED_FAT_KEYWORDS))

    for code, keywords in keyword_checks:
        for i, meal in enumerate(meals):
            for j, item in enumerate(meal.get("items", [])):
                name = (item.get("name") or "").lower()
                for kw in keywords:
                    if kw in name:
                        violations.append(_violation(
                            code, "revise",
                            f"'{item.get('name')}' may be risky given declared medical condition(s).",
                            f"meals[{i}].items[{j}]",
                        ))
    return violations


def _check_value_bounds(meals: list) -> list[dict]:
    violations = []
    if not (_MIN_MEALS <= len(meals) <= _MAX_MEALS):
        violations.append(_violation("MEAL_COUNT_OUT_OF_BOUNDS", "revise", f"{len(meals)} meals is outside [{_MIN_MEALS}, {_MAX_MEALS}]."))
    for i, meal in enumerate(meals):
        for j, item in enumerate(meal.get("items", [])):
            calories = item.get("calories", 0) or 0
            if not (0 <= calories <= _MAX_ITEM_CALORIES):
                violations.append(_violation(
                    "ITEM_CALORIES_OUT_OF_BOUNDS", "revise",
                    f"'{item.get('name')}' has {calories} kcal, outside [0, {_MAX_ITEM_CALORIES}].",
                    f"meals[{i}].items[{j}].calories",
                ))
    return violations


def validate_plan(meals: list, targets: dict, prefs: dict) -> dict:
    """Runs all rule checks and returns {"verdict": "pass"|"revise"|"reject", "violations": [...]}.

    Short-circuits to reject on schema failure, since it's unsafe to run
    numeric/keyword checks against malformed data.
    """
    violations = _check_schema(meals)
    if any(v["severity"] == "reject" for v in violations):
        return {"verdict": "reject", "violations": violations}

    totals = _sum_meal_totals(meals)
    violations += _check_calorie_tolerance(totals, targets)
    violations += _check_macro_sanity(totals)
    violations += _check_restrictions_and_dislikes(meals, prefs)
    violations += _check_medical_conditions(meals, targets, prefs)
    violations += _check_value_bounds(meals)

    if any(v["severity"] == "reject" for v in violations):
        verdict = "reject"
    elif violations:
        verdict = "revise"
    else:
        verdict = "pass"

    return {"verdict": verdict, "violations": violations}
