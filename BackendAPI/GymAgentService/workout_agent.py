"""GymAgentService/workout_agent.py — suggests possible workouts for a gym.

A single LLM call (no tools/scraping needed): the gym's equipment and classes
are already known from the enrichment agent, so this just asks the model to
turn that list into a handful of structured workout suggestions.
"""

import asyncio
import json
import logging
import os
import re

import openai
from langchain_core.messages import HumanMessage, SystemMessage

from llm_config import get_llm
from schemas import WorkoutSuggestions

logger = logging.getLogger("gym_agent")

MAX_RETRIES = int(os.getenv("AGENT_MAX_RETRIES", "2"))

SYSTEM_PROMPT = (
    "You are a fitness coach for the VitroFit app. Given a gym's name and its available "
    "equipment/classes, suggest EXACTLY 4 varied, practical workouts a visitor could do there today. "
    "Prefer workouts that make direct use of the listed equipment/classes, and vary the "
    "categories and difficulty levels rather than repeating the same type of workout. "
    "If little or no equipment/class info is given, suggest generic workouts a person could do "
    "with typical gym basics or just bodyweight, and explain that in the notes field. "
    "Keep every description to 1-2 short sentences — be concise, not exhaustive. "
    "For each workout's equipment_used, list only the 1-3 most relevant items — never repeat "
    "the gym's entire equipment/class list for every workout, even if the gym has many items."
)

JSON_SYSTEM_PROMPT = SYSTEM_PROMPT + (
    "\n\nRespond with ONLY a JSON object of this exact shape, no other text:\n"
    '{"workouts": [{"name": "...", "category": "...", "duration_minutes": 30, '
    '"difficulty": "Beginner|Intermediate|Advanced", "description": "...", '
    '"equipment_used": ["..."]}], "notes": "..."}'
)


def _build_messages(name: str, equipment: list[str], classes: list[str], system_prompt: str) -> list:
    equipment_str = ", ".join(equipment) if equipment else "unknown / not listed"
    classes_str = ", ".join(classes) if classes else "unknown / not listed"

    user_msg = HumanMessage(
        content=(
            f"Gym: {name}\n"
            f"Available equipment: {equipment_str}\n"
            f"Available classes: {classes_str}\n\n"
            "Suggest workouts for a visitor to this gym."
        )
    )
    return [SystemMessage(content=system_prompt), user_msg]


def _structured_call(name: str, equipment: list[str], classes: list[str]) -> dict:
    llm = get_llm(temperature=0.4, max_tokens=900)
    structured_llm = llm.with_structured_output(WorkoutSuggestions)
    messages = _build_messages(name, equipment, classes, SYSTEM_PROMPT)
    result: WorkoutSuggestions = structured_llm.invoke(messages)
    return {
        "workouts": [w.model_dump() for w in result.workouts],
        "notes": result.notes,
    }


def _fallback_json_call(name: str, equipment: list[str], classes: list[str]) -> dict:
    """Fallback when structured (function-calling) output isn't supported/working.

    Raises on failure instead of returning an empty "success" — a genuine failure
    should surface as an error to the caller, not silently look like a real
    (if empty) answer.
    """
    llm = get_llm(temperature=0.4, max_tokens=900)
    messages = _build_messages(name, equipment, classes, JSON_SYSTEM_PROMPT)
    response = llm.invoke(messages)
    raw = response.content or ""

    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group())
            return {
                "workouts": data.get("workouts", []),
                "notes": data.get("notes", ""),
            }
        except json.JSONDecodeError as e:
            raise ValueError("Could not parse workout suggestions from model output") from e

    raise ValueError("Model output did not contain a JSON object")


async def suggest_workouts(name: str, equipment: list[str], classes: list[str]) -> dict:
    """Generate structured workout suggestions for a gym.

    Returns: {"workouts": list[dict], "notes": str} or {"workouts": [], "notes": "", "error": str}
    """
    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            return await asyncio.to_thread(_structured_call, name, equipment, classes)
        except (openai.APIConnectionError, openai.RateLimitError, openai.InternalServerError) as e:
            last_error = e
            logger.warning(
                "Transient error generating workouts for %r (attempt %d/%d): %s",
                name, attempt + 1, MAX_RETRIES + 1, e,
            )
            if attempt < MAX_RETRIES:
                await asyncio.sleep(1.5 * (attempt + 1))
        except Exception as e:
            # Structured output (function calling) may not be supported by the
            # current model — retry once with a plain-JSON prompt instead of failing.
            logger.warning("Structured output failed for %r, falling back to JSON prompt: %s", name, e)
            try:
                return await asyncio.to_thread(_fallback_json_call, name, equipment, classes)
            except Exception as fallback_error:
                last_error = fallback_error
                logger.exception("Fallback workout generation also failed for %r", name)
                break

    return {"workouts": [], "notes": "", "error": str(last_error)}
