# DietPlanService/tests/test_tools.py
"""generate_meals / refine_meals with the model call scripted: no network, no real LLM."""
import json

import pytest

import src.tools.tools as tools
from conftest import make_meals

TARGETS = {"totalCalories": 2000, "macros": {"protein": 150, "carbs": 200, "fat": 60}}
PREFS = {"mealFrequency": "3Meals", "restrictions": [], "dislikes": "", "budgetTier": "medium", "cookingTime": "moderate"}


def _reply(calories_each, count=4, name="Rice bowl"):
    return json.dumps({"meals": make_meals(calories_each, name=name, count=count)})


@pytest.fixture
def scripted_model(monkeypatch):
    """Replaces the single low-level model call with a queue of replies (or exceptions)."""
    calls = []
    queue = []

    async def fake_call_model(model_id, prompt, system_instruction=None):
        calls.append({"model": model_id, "prompt": prompt, "system": system_instruction})
        reply = queue.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(tools, "call_model", fake_call_model)
    return type("Script", (), {"queue": queue, "calls": calls})


def test_parse_llm_json_handles_fences_prose_and_garbage():
    good = '```json\n{"meals": [{"type": "x"}]}\n```'
    assert tools._parse_llm_json(good) == {"meals": [{"type": "x"}]}
    assert tools._parse_llm_json('Sure! {"meals": [{"type": "x"}]} Enjoy') is not None
    assert tools._parse_llm_json("") is None
    assert tools._parse_llm_json(None) is None
    assert tools._parse_llm_json("no json here") is None
    assert tools._parse_llm_json("{not valid json}") is None
    assert tools._parse_llm_json('{"meals": []}') is None
    assert tools._parse_llm_json('{"meals": "nope"}') is None


def test_totals_and_tolerance():
    totals = tools._sum_totals(make_meals(500.0, count=4))
    assert totals["calories"] == 2000
    assert tools._within_tolerance(totals, TARGETS)
    assert tools._within_tolerance({"calories": 2199}, TARGETS) and not tools._within_tolerance({"calories": 2300}, TARGETS)
    assert tools._within_tolerance({"calories": 1}, {"totalCalories": 0})
    assert tools._sum_totals([{"items": [{"calories": None, "macros": None}]}])["calories"] == 0


@pytest.mark.asyncio
async def test_generate_meals_success_on_target(scripted_model):
    scripted_model.queue.append(_reply(500))
    result = await tools.generate_meals(TARGETS, PREFS)
    assert result["withinTolerance"] is True and len(result["meals"]) == 4
    assert len(scripted_model.calls) == 1


@pytest.mark.asyncio
async def test_generate_meals_retries_once_when_off_target(scripted_model):
    scripted_model.queue.extend([_reply(300), _reply(500)])
    result = await tools.generate_meals(TARGETS, PREFS)
    assert result["withinTolerance"] is True
    assert len(scripted_model.calls) == 2
    assert "previous attempt totalled" in scripted_model.calls[1]["prompt"]


@pytest.mark.asyncio
async def test_generate_meals_gives_closest_attempt_when_retry_still_off(scripted_model):
    scripted_model.queue.extend([_reply(300), _reply(400)])
    result = await tools.generate_meals(TARGETS, PREFS)
    assert result["withinTolerance"] is False
    assert tools._sum_totals(result["meals"])["calories"] == 1600  # the retry's meals


@pytest.mark.asyncio
async def test_generate_meals_keeps_first_attempt_when_retry_fails(scripted_model):
    scripted_model.queue.extend([_reply(300), RuntimeError("boom")])
    result = await tools.generate_meals(TARGETS, PREFS)
    assert result["withinTolerance"] is False and tools._sum_totals(result["meals"])["calories"] == 1200


@pytest.mark.asyncio
async def test_generate_meals_falls_back_to_the_second_model(scripted_model, monkeypatch):
    monkeypatch.setattr(tools, "PRIMARY_MODEL", "primary")
    monkeypatch.setattr(tools, "FALLBACK_MODEL", "fallback")
    scripted_model.queue.extend([RuntimeError("primary down"), _reply(500)])
    result = await tools.generate_meals(TARGETS, PREFS)
    assert result["withinTolerance"] is True
    assert [c["model"] for c in scripted_model.calls] == ["primary", "fallback"]


@pytest.mark.asyncio
async def test_generate_meals_reports_unavailable_and_unreadable_cleanly(scripted_model):
    scripted_model.queue.extend([RuntimeError("down"), RuntimeError("down")])
    assert "temporarily unavailable" in (await tools.generate_meals(TARGETS, PREFS))["error"]
    scripted_model.queue.extend(["I cannot help with that"])
    assert "unreadable" in (await tools.generate_meals(TARGETS, PREFS))["error"]


@pytest.mark.asyncio
async def test_failures_are_logged_without_the_prompt_or_error_text(scripted_model, caplog):
    scripted_model.queue.extend([RuntimeError("secret prompt text nvapi-ABCDEFGH12345678"), RuntimeError("x")])
    with caplog.at_level("WARNING", logger="diet_agent"):
        await tools.generate_meals(TARGETS, dict(PREFS, dislikes="PRIVATE-DISLIKE"))
    assert "llm call failed" in caplog.text
    assert "PRIVATE-DISLIKE" not in caplog.text and "nvapi" not in caplog.text


@pytest.mark.asyncio
async def test_refine_meals_uses_the_refine_instruction_and_current_plan(scripted_model):
    scripted_model.queue.append(_reply(500, name="Quinoa bowl"))
    current = make_meals(500.0, name="Rice bowl", count=4)
    result = await tools.refine_meals(TARGETS, PREFS, current, "swap the rice")
    assert result["meals"][0]["items"][0]["name"] == "Quinoa bowl" and result["withinTolerance"] is True
    sent = json.loads(scripted_model.calls[0]["prompt"])
    assert sent["userRequestedChange"] == "swap the rice" and sent["currentPlan"]["meals"] == current
    assert "revising an existing meal plan" in scripted_model.calls[0]["system"]


@pytest.mark.asyncio
async def test_refine_meals_error_paths(scripted_model):
    scripted_model.queue.extend([RuntimeError("down"), RuntimeError("down")])
    assert "temporarily unavailable" in (await tools.refine_meals(TARGETS, PREFS, [], "x"))["error"]
    scripted_model.queue.append("nonsense")
    assert "unreadable" in (await tools.refine_meals(TARGETS, PREFS, [], "x"))["error"]


@pytest.mark.asyncio
async def test_meal_generator_agent_maps_tool_errors(monkeypatch):
    import src.agent.nodes.meal_generator as node
    from src.models.contracts import MealGeneratorInput

    async def failing(*args, **kwargs):
        return {"error": "The meal-planning service is temporarily unavailable. Please try again."}

    monkeypatch.setattr(node, "generate_meals", failing)
    out = await node.MealGeneratorAgent().run(MealGeneratorInput(targets=TARGETS, prefs=PREFS))
    assert out.error and out.meals == []

    seen = {}

    async def capture(targets, prefs):
        seen.update(prefs)
        return {"meals": make_meals(500.0, count=4), "withinTolerance": True}

    monkeypatch.setattr(node, "generate_meals", capture)
    await node.MealGeneratorAgent().run(MealGeneratorInput(targets=TARGETS, prefs=PREFS, corrective_note="too low"))
    assert seen["_corrective_note"] == "too low"
