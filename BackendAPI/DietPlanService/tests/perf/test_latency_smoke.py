"""Latency smoke tests with generous limits. They exist to catch an accidental slow path (a validator
that becomes quadratic, an audit write that blocks), not to benchmark. The model call, which dominates
a real run, is replaced by an instant fake, so these numbers are the service's own overhead."""
import statistics
import time

import pytest

from conftest import VALID_PREFS, expected_target_calories, make_meals
from src.agent.nodes import planner
from src.agent.workflow import run_workflow
from src.utils import injection_guard
from src.utils.db import SessionLocal
from src.utils.validators import validate_plan

pytestmark = pytest.mark.perf

TARGET = expected_target_calories(VALID_PREFS)


def _time(fn, repeat=200):
    samples = []
    for _ in range(repeat):
        start = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - start) * 1000)
    return statistics.median(samples), max(samples)


def test_validator_is_fast_even_for_a_large_plan():
    meals = make_meals(100.0, count=8)
    for meal in meals:
        meal["items"] = meal["items"] * 10
    median, worst = _time(lambda: validate_plan(meals, {"totalCalories": 8000, "macros": {}}, VALID_PREFS), repeat=50)
    assert median < 50 and worst < 500, (median, worst)


def test_injection_guard_is_fast_on_long_input():
    text = "I do not like onions, brinjal or bitter gourd. " * 40
    median, worst = _time(lambda: injection_guard.guard_field(text, limit=500))
    assert median < 20 and worst < 200, (median, worst)
    median, worst = _time(lambda: injection_guard.scan("ignore " * 3000), repeat=20)
    assert worst < 1000, worst  # bounded work on pathological input


def test_planner_is_effectively_free():
    median, _ = _time(lambda: planner.run("generate_diet_plan", VALID_PREFS))
    assert median < 5


@pytest.mark.asyncio
async def test_a_whole_run_without_the_model_is_quick(mock_generate_meals):
    mock_generate_meals.return_value = {"meals": make_meals(TARGET / 4, count=4), "withinTolerance": True}
    session = SessionLocal()
    try:
        started = time.perf_counter()
        wf = await run_workflow("generate_diet_plan", dict(VALID_PREFS), user_id=1, session=session)
        elapsed_ms = (time.perf_counter() - started) * 1000
    finally:
        session.close()
    assert wf.status == "completed"
    assert elapsed_ms < 3000, elapsed_ms
