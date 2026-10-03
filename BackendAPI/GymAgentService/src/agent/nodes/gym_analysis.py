"""Gym analysis agent: gathers evidence with tools, then extracts structured facts.

Contract: AnalysisInput -> GymFacts (+ the sanitised text it saw, for the validator).
Tools: scrape_gym_website, search_gym_info, lookup_similar_gyms, narrowed by the plan
and always invoked through tool_registry.call_tool (allow-list, guards, timeouts).
"""

import os
import re
from typing import Callable

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from src.agent.nodes._common import (
    TRANSIENT_ERRORS,
    AgentOutputError,
    parse_json_object,
    untrusted,
    with_retries,
)
from src.models.contracts import AnalysisInput, GymFacts
from src.tools.tool_registry import ToolResult, call_tool, sanitize_untrusted_text, tools_for
from src.utils.injection_guard import guard_field
from src.tools.url_policy import configured_allowlist, normalise_host
from src.prompts.agent_prompts import GYM_ANALYSIS_EXTRACTION_PROMPT, GYM_ANALYSIS_JSON_SHAPE
from src.prompts.system_prompts import GYM_ANALYSIS_SYSTEM_PROMPT

MAX_AGENT_STEPS = int(os.getenv("AGENT_MAX_STEPS", "6"))
NO_EVIDENCE_CONFIDENCE_CAP = 0.3

def _task_message(inp: AnalysisInput) -> HumanMessage:
    gym = inp.gym

    def clean(value):
        # OSM-supplied fields are editable by anyone: normalise them before they reach the prompt.
        return guard_field(value).text if value else value

    parts = [f"Gym: {clean(gym.name)}", f"Address: {clean(gym.address) or 'unknown'}"]
    parts.append(f"Website: {gym.website}" if gym.website else "Website: none")
    parts.append(f"Allowed tools this run: {', '.join(inp.plan.analysis_tools)}")
    own = normalise_host(gym.website) if gym.website else ""
    sources = ([own] if own else []) + configured_allowlist()
    parts.append(f"Allowed evidence sources (cite only these hosts): {', '.join(sources) or 'none'}")
    known = [
        f"{label} = {clean(value)}"
        for label, value in (
            ("phone", gym.known_phone),
            ("email", gym.known_email),
            ("opening hours", gym.known_hours),
        )
        if value
    ]
    if known:
        parts.append("Already verified (do not search for these): " + ", ".join(known))
    if inp.feedback:
        parts.append(
            "Fix these problems from the previous attempt:\n- "
            + "\n- ".join(sanitize_untrusted_text(f, 300) for f in inp.feedback)
        )
    return HumanMessage(content="\n".join(parts))


_SOURCE_LINE = re.compile(r"^Source:\s*(https?://\S+)", re.MULTILINE)


def _urls_from(name: str, args: dict, output: str) -> list[str]:
    """Pages a successful tool call actually retrieved (what evidence may legitimately cite)."""
    if name == "scrape_gym_website":
        url = str(args.get("url") or "")
        return [url] if url else []
    if name == "search_gym_info":
        return _SOURCE_LINE.findall(output)
    return []


def _summarise(name: str, args: dict) -> str:
    return str(args.get("url") or args.get("query") or args.get("gym_name") or name)[:200]


async def _extract(llm, messages: list) -> GymFacts:
    try:
        structured = llm.with_structured_output(GymFacts)
        result = await with_retries(
            lambda: structured.ainvoke(messages + [HumanMessage(content=GYM_ANALYSIS_EXTRACTION_PROMPT)]),
            what="gym_analysis.extract",
        )
        if isinstance(result, GymFacts):
            return result
        return GymFacts.model_validate(result)
    except Exception as exc:
        if isinstance(exc, TRANSIENT_ERRORS):
            raise  # retries already exhausted; do not mask as a parse problem
    # Model without function calling: ask for plain JSON and validate it ourselves.
    response = await with_retries(
        lambda: llm.ainvoke(messages + [HumanMessage(content=GYM_ANALYSIS_EXTRACTION_PROMPT + GYM_ANALYSIS_JSON_SHAPE)]),
        what="gym_analysis.extract_json",
    )
    try:
        return GymFacts.model_validate(parse_json_object(response.content or ""))
    except Exception as exc:
        raise AgentOutputError("gym_analysis output invalid") from exc


async def run(
    inp: AnalysisInput, llm_factory: Callable[..., object]
) -> tuple[GymFacts, list[str], list[str], list[dict]]:
    """Returns (facts, sanitised tool text corpus, retrieved URLs, tool-call records)."""
    llm = llm_factory(temperature=0.1, max_tokens=900)
    allowed = inp.plan.analysis_tools
    bound = llm.bind_tools(tools_for("gym_analysis", allowed))

    messages: list = [SystemMessage(content=GYM_ANALYSIS_SYSTEM_PROMPT), _task_message(inp)]
    corpus: list[str] = []
    sources: list[str] = []
    records: list[dict] = []

    for _ in range(MAX_AGENT_STEPS):
        response = await with_retries(lambda: bound.ainvoke(messages), what="gym_analysis.reason")
        messages.append(response)
        calls = getattr(response, "tool_calls", None) or []
        if not calls:
            break
        for call in calls:
            name, args = call["name"], call.get("args") or {}
            try:
                result = await call_tool(
                    "gym_analysis", name, args, allowed=allowed, website=inp.gym.website
                )
            except PermissionError:
                result = ToolResult(name, False, "", "NOT_ALLOWED", 0)
            records.append(
                {
                    "agent": "gym_analysis",
                    "tool": name,
                    "ok": result.ok,
                    "error": result.error_code,
                    "durationMs": result.duration_ms,
                    "input": _summarise(name, args),
                    "flags": ",".join(result.flags),
                }
            )
            if result.ok and result.output:
                corpus.append(result.output)
                sources.extend(u for u in _urls_from(name, args, result.output) if u not in sources)
            content = (
                untrusted(result.output)
                if result.ok
                else f"Tool '{name}' failed: {result.error_code}. Try another allowed tool."
            )
            messages.append(ToolMessage(content=content, tool_call_id=call["id"], name=name))

    facts = await _extract(llm_factory(temperature=0.1, max_tokens=900), messages)

    updates: dict = {}
    # Trusted map-provider values always win over anything the model produced.
    for field, known in (
        ("phone", inp.gym.known_phone),
        ("email", inp.gym.known_email),
        ("opening_hours", inp.gym.known_hours),
    ):
        if known:
            updates[field] = known
    # Without any retrieved text the model cannot honestly claim high confidence.
    if not corpus:
        updates["confidence"] = min(facts.confidence, NO_EVIDENCE_CONFIDENCE_CAP)
    if updates:
        facts = facts.model_copy(update=updates)
    return facts, corpus, sources, records
