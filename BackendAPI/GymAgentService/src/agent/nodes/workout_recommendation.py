"""Workout recommendation agent: turns validated-shape facts into four workouts.

Contract: RecommendInput -> Recommendations. Its only tool is the read-only,
offline list_equipment_taxonomy (no network, no gym data). It never sees contact
details, only the gym name and the equipment/classes lists.
"""

from typing import Callable

from langchain_core.messages import HumanMessage, SystemMessage

from src.agent.nodes._common import (
    TRANSIENT_ERRORS,
    AgentOutputError,
    parse_json_object,
    with_retries,
)
from src.models.contracts import RecommendInput, Recommendations
from src.utils.injection_guard import guard_field
from src.tools.tool_registry import call_tool, sanitize_untrusted_text
from src.prompts.agent_prompts import WORKOUT_RECOMMENDATION_JSON_SHAPE
from src.prompts.system_prompts import WORKOUT_RECOMMENDATION_SYSTEM_PROMPT

def _messages(inp: RecommendInput, taxonomy: str, json_mode: bool) -> list:
    equipment = ", ".join(inp.facts.equipment) or "none listed"
    classes = ", ".join(inp.facts.classes) or "none listed"
    parts = [
        f"Gym: {guard_field(inp.name).text}",   # OSM-supplied: normalised before it reaches the prompt
        f"Verified equipment: {equipment}",
        f"Verified classes: {classes}",
        f"Taxonomy: {taxonomy}",
    ]
    if inp.feedback:
        parts.append(
            "Fix these problems from the previous attempt:\n- "
            + "\n- ".join(sanitize_untrusted_text(f, 300) for f in inp.feedback)
        )
    parts.append("Suggest workouts for a visitor to this gym.")
    system = WORKOUT_RECOMMENDATION_SYSTEM_PROMPT + (WORKOUT_RECOMMENDATION_JSON_SHAPE if json_mode else "")
    return [SystemMessage(content=system), HumanMessage(content="\n".join(parts))]


async def run(
    inp: RecommendInput, llm_factory: Callable[..., object]
) -> tuple[Recommendations, list[dict]]:
    """Returns (recommendations, tool-call records)."""
    tool = await call_tool("workout_recommendation", "list_equipment_taxonomy", {})
    records = [
        {
            "agent": "workout_recommendation",
            "tool": tool.tool,
            "ok": tool.ok,
            "error": tool.error_code,
            "durationMs": tool.duration_ms,
            "input": "",
        }
    ]
    taxonomy = tool.output if tool.ok else "{}"

    llm = llm_factory(temperature=0.4, max_tokens=1100)
    try:
        structured = llm.with_structured_output(Recommendations)
        result = await with_retries(
            lambda: structured.ainvoke(_messages(inp, taxonomy, json_mode=False)),
            what="workout_recommendation.structured",
        )
        recs = result if isinstance(result, Recommendations) else Recommendations.model_validate(result)
        return recs, records
    except Exception as exc:
        if isinstance(exc, TRANSIENT_ERRORS):
            raise

    response = await with_retries(
        lambda: llm.ainvoke(_messages(inp, taxonomy, json_mode=True)),
        what="workout_recommendation.json",
    )
    try:
        return Recommendations.model_validate(parse_json_object(response.content or "")), records
    except Exception as exc:
        raise AgentOutputError("workout_recommendation output invalid") from exc
