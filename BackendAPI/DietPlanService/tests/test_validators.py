# DietPlanService/tests/test_validators.py
from validators import validate_plan
from conftest import make_meals, VALID_PREFS


def test_validate_plan_pass_within_tolerance():
    targets = {"totalCalories": 2000, "macros": {"protein": 150, "carbs": 200, "fat": 60}}
    meals = make_meals(calories_each=500.0, count=4)  # 2000 total, exactly on target
    result = validate_plan(meals, targets, VALID_PREFS)
    assert result["verdict"] == "pass"
    assert result["violations"] == []


def test_validate_plan_revise_on_calorie_drift():
    targets = {"totalCalories": 2000, "macros": {}}
    meals = make_meals(calories_each=575.0, count=4)  # 2300, 15% over -> revise
    result = validate_plan(meals, targets, VALID_PREFS)
    assert result["verdict"] == "revise"
    assert any(v["code"] == "CALORIE_OUT_OF_TOLERANCE" for v in result["violations"])


def test_validate_plan_revise_not_reject_on_large_calorie_miss():
    # A real generation can miss by well over 25%; the reject threshold (0.50)
    # should still give this a revise chance rather than rejecting outright.
    targets = {"totalCalories": 2594, "macros": {}}
    meals = make_meals(calories_each=1725.0 / 4, count=4)  # 34% under target
    result = validate_plan(meals, targets, VALID_PREFS)
    assert result["verdict"] == "revise"


def test_validate_plan_reject_on_restriction_violation():
    targets = {"totalCalories": 2000, "macros": {}}
    meals = make_meals(calories_each=500.0, name="Grilled chicken breast", count=4)
    prefs = dict(VALID_PREFS, restrictions=["vegetarian"])
    result = validate_plan(meals, targets, prefs)
    assert result["verdict"] == "reject"
    assert any(v["code"] == "RESTRICTION_VIOLATION" for v in result["violations"])


def test_validate_plan_reject_below_calorie_floor_with_medical_condition():
    targets = {"totalCalories": 1000, "macros": {}}
    meals = make_meals(calories_each=250.0, count=4)
    prefs = dict(VALID_PREFS, medicalConditions=["diabetes"])
    result = validate_plan(meals, targets, prefs)
    assert result["verdict"] == "reject"
    assert any(v["code"] == "BELOW_SAFE_FLOOR" for v in result["violations"])
