"""
GymAgentService/enrichment_agent.py — LangGraph-powered gym enrichment agent.

Architecture:
  START → prepare_context → agent_reasoning ⇄ tool_execution → extract_structured → validate → END
                                                                                        ↓ (low confidence)
                                                                                    fallback_generic → END

The agent autonomously decides which tools to use (scrape website, web search,
DB lookup) and then extracts structured equipment/class data with guaranteed
Pydantic output.
"""

import asyncio
import json
import logging
import os
import re
import uuid
from typing import Annotated, Literal

import openai

from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv

from llm_config import get_llm
from schemas import GymEnrichmentResult
from tools import get_all_tools

load_dotenv()

CONFIDENCE_THRESHOLD = float(os.getenv("AGENT_CONFIDENCE_THRESHOLD", "0.6"))
MAX_AGENT_STEPS = int(os.getenv("AGENT_MAX_STEPS", "6"))
MAX_RETRIES = int(os.getenv("AGENT_MAX_RETRIES", "2"))

logger = logging.getLogger("gym_agent")


# ── 1. State Definition ─────────────────────────────────────────────────


class GymEnrichmentState(TypedDict):
    """State that flows through the enrichment graph."""

    # Agent conversation (LLM messages + tool calls/results)
    messages: Annotated[list[BaseMessage], add_messages]
    # Input context
    gym_name: str
    gym_address: str | None
    gym_website: str | None
    known_phone: str | None
    known_email: str | None
    known_hours: str | None
    # Output
    result: dict | None
    source: str
    step_count: int


# ── 2. Graph Nodes ───────────────────────────────────────────────────────


def prepare_context(state: GymEnrichmentState) -> dict:
    """Build the initial prompt with gym info and instructions."""
    name = state["gym_name"]
    address = state.get("gym_address") or "unknown"
    website = state.get("gym_website")
    known_phone = state.get("known_phone")
    known_email = state.get("known_email")
    known_hours = state.get("known_hours")

    system_msg = SystemMessage(
        content=(
            "You are a gym data enrichment agent for the VitroFit fitness app. "
            "Your goal is to find accurate equipment, class, and contact information for a specific gym.\n\n"
            "STRATEGY:\n"
            "1. If a website URL is provided, ALWAYS try scraping it first with scrape_gym_website.\n"
            "2. If scraping fails or returns little info, try search_gym_info with a specific query.\n"
            "3. If search also fails, try lookup_similar_gyms for reference data.\n"
            "4. After gathering information, provide your final answer.\n\n"
            "Be thorough but efficient — don't call tools unnecessarily if you already have enough info.\n\n"
            "CONTACT DETAILS RULE (important): only report a phone number, email, or opening hours "
            "if you actually see it written in the scraped website text or search results. "
            "Never guess, infer, or invent a phone number, email, or opening hours — leave the field "
            "empty/null if you didn't find it explicitly stated."
        )
    )

    user_msg_parts = [
        f"Find equipment, classes, and contact details for this gym:\n- Name: {name}\n- Address: {address}"
    ]
    if website:
        user_msg_parts.append(
            f"- Website: {website}\n\nStart by scraping the website."
        )
    else:
        user_msg_parts.append(
            "\nNo website is available. Try searching the web for this gym."
        )

    known_parts = []
    if known_phone:
        known_parts.append(f"phone = {known_phone}")
    if known_email:
        known_parts.append(f"email = {known_email}")
    if known_hours:
        known_parts.append(f"opening hours = {known_hours}")
    if known_parts:
        user_msg_parts.append(
            "\nWe already know the following (no need to search for these): "
            + ", ".join(known_parts)
            + ". Focus your search on equipment/classes and any of the above that's still missing."
        )

    user_msg = HumanMessage(content="\n".join(user_msg_parts))

    return {
        "messages": [system_msg, user_msg],
        "step_count": 0,
        "source": "ai-scraped" if website else "ai-generic",
    }


def agent_reasoning(state: GymEnrichmentState) -> dict:
    """The LLM reasons about what to do next — call a tool or give a final answer."""
    llm = get_llm()
    tools = get_all_tools()
    llm_with_tools = llm.bind_tools(tools)

    response = llm_with_tools.invoke(state["messages"])
    return {
        "messages": [response],
        "step_count": state.get("step_count", 0) + 1,
    }


def extract_structured(state: GymEnrichmentState) -> dict:
    """Extract structured equipment/classes from the conversation using guaranteed Pydantic output."""
    llm = get_llm(temperature=0.1)

    # Try structured output (works with models that support function calling)
    try:
        structured_llm = llm.with_structured_output(GymEnrichmentResult)

        extraction_prompt = HumanMessage(
            content=(
                "Based on our conversation above, extract the final structured data.\n"
                "List all equipment and classes you found. Set confidence based on data quality:\n"
                "- 0.8-1.0 if data came directly from the gym's website\n"
                "- 0.5-0.7 if data came from web search or reviews\n"
                "- 0.2-0.4 if you're guessing based on the gym name/type\n\n"
                "Also fill in phone, email, and opening_hours ONLY if explicitly present in the "
                "scraped/searched content above — leave them null if not found. Do not invent them."
            )
        )

        messages = list(state["messages"]) + [extraction_prompt]
        result: GymEnrichmentResult = structured_llm.invoke(messages)

        return {
            "result": {
                "source": state.get("source", "ai-generic"),
                "equipment": result.equipment,
                "classes": result.classes,
                "confidence": result.confidence,
                "reasoning": result.reasoning,
                "phone": result.phone,
                "email": result.email,
                "opening_hours": result.opening_hours,
            }
        }
    except Exception:
        # Fallback: ask the LLM normally and parse manually
        return _fallback_extraction(state)


def _fallback_extraction(state: GymEnrichmentState) -> dict:
    """Fallback extraction when structured output isn't supported by the model."""
    llm = get_llm(temperature=0.1)
    extraction_prompt = HumanMessage(
        content=(
            "Based on our conversation, respond with ONLY a JSON object:\n"
            '{"equipment": ["item1", "item2"], "classes": ["class1", "class2"], '
            '"confidence": 0.5, "reasoning": "brief explanation", '
            '"phone": null, "email": null, "opening_hours": null}\n\n'
            "Only fill in phone/email/opening_hours if explicitly present in the conversation above "
            "— leave them null if not found. Do not invent them."
        )
    )

    messages = list(state["messages"]) + [extraction_prompt]
    response = llm.invoke(messages)
    raw = response.content or ""

    # Parse JSON from response
    json_match = re.search(r"\{[^{}]*\}", raw, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group())
            return {
                "result": {
                    "source": state.get("source", "ai-generic"),
                    "equipment": data.get("equipment", []),
                    "classes": data.get("classes", []),
                    "confidence": data.get("confidence", 0.3),
                    "reasoning": data.get("reasoning", "Parsed from fallback"),
                    "phone": data.get("phone"),
                    "email": data.get("email"),
                    "opening_hours": data.get("opening_hours"),
                }
            }
        except json.JSONDecodeError:
            pass

    return {
        "result": {
            "source": "ai-generic",
            "equipment": [],
            "classes": [],
            "confidence": 0.1,
            "reasoning": "Failed to extract structured data",
        }
    }


def validate_result(state: GymEnrichmentState) -> dict:
    """Validate the extraction result and set final source tag."""
    result = state.get("result")
    if not result:
        return {
            "result": {
                "source": "ai-generic",
                "equipment": [],
                "classes": [],
                "confidence": 0.0,
                "reasoning": "No result produced",
                "phone": None,
                "email": None,
                "opening_hours": None,
            }
        }

    # Make a copy so we don't mutate the original
    result = dict(result)
    confidence = result.get("confidence", 0)

    # Set source based on confidence
    if confidence >= 0.7:
        result["source"] = "ai-scraped"
    elif confidence >= 0.4:
        result["source"] = "ai-inferred"
    else:
        result["source"] = "ai-generic"

    return {"result": result}


# ── 3. Routing Functions ────────────────────────────────────────────────


def should_continue_or_extract(
    state: GymEnrichmentState,
) -> Literal["tools", "extract_structured"]:
    """After agent reasoning: if it called tools → execute them, otherwise → extract."""
    # Check if max steps reached
    if state.get("step_count", 0) >= MAX_AGENT_STEPS:
        return "extract_structured"

    # Use LangGraph's built-in tool detection
    result = tools_condition(state)

    # tools_condition returns "__end__" when no tool calls are present
    if result == "__end__":
        return "extract_structured"

    return result


# ── 4. Build the Graph ──────────────────────────────────────────────────


def _build_graph() -> StateGraph:
    tools = get_all_tools()

    graph = StateGraph(GymEnrichmentState)

    # Add nodes
    graph.add_node("prepare_context", prepare_context)
    graph.add_node("agent_reasoning", agent_reasoning)
    graph.add_node("tools", ToolNode(tools))
    graph.add_node("extract_structured", extract_structured)
    graph.add_node("validate_result", validate_result)

    # Add edges
    graph.add_edge(START, "prepare_context")
    graph.add_edge("prepare_context", "agent_reasoning")

    # After reasoning: either use tools or extract final answer
    graph.add_conditional_edges(
        "agent_reasoning",
        should_continue_or_extract,
        {
            "tools": "tools",
            "extract_structured": "extract_structured",
        },
    )

    # After tool execution: back to reasoning
    graph.add_edge("tools", "agent_reasoning")

    # After extraction: validate
    graph.add_edge("extract_structured", "validate_result")

    # After validation: done
    graph.add_edge("validate_result", END)

    return graph


# Compile once at module level with in-memory checkpointer
_checkpointer = MemorySaver()
_compiled_graph = _build_graph().compile(checkpointer=_checkpointer)


# ── 5. Public API (same interface as before) ────────────────────────────


async def enrich_gym(
    name: str,
    address: str | None,
    website: str | None,
    known_phone: str | None = None,
    known_email: str | None = None,
    known_hours: str | None = None,
) -> dict:
    """Enrich a gym with equipment, class, and contact data using the LangGraph agent.

    `known_*` are already-verified values (e.g. from OSM/Geoapify) — they're passed to
    the agent as hints so it doesn't need to re-discover them, and they always win over
    an AI-found value in the returned dict.

    Returns: {"source": str, "equipment": list, "classes": list,
              "phone": str | None, "email": str | None, "opening_hours": str | None}
    """
    initial_state: GymEnrichmentState = {
        "messages": [],
        "gym_name": name,
        "gym_address": address,
        "gym_website": website,
        "known_phone": known_phone,
        "known_email": known_email,
        "known_hours": known_hours,
        "result": None,
        "source": "ai-generic",
        "step_count": 0,
    }

    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        try:
            final_state = await _compiled_graph.ainvoke(initial_state, config=config)
            result = final_state.get("result", {})
            return {
                "source": result.get("source", "ai-generic"),
                "equipment": result.get("equipment", []),
                "classes": result.get("classes", []),
                "phone": known_phone or result.get("phone"),
                "email": known_email or result.get("email"),
                "opening_hours": known_hours or result.get("opening_hours"),
            }
        except (openai.APIConnectionError, openai.RateLimitError, openai.InternalServerError) as e:
            last_error = e
            logger.warning(
                "Transient error enriching %r (attempt %d/%d): %s",
                name, attempt + 1, MAX_RETRIES + 1, e,
            )
            if attempt < MAX_RETRIES:
                await asyncio.sleep(1.5 * (attempt + 1))
        except Exception as e:
            return {
                "source": "ai-generic",
                "equipment": [],
                "classes": [],
                "phone": known_phone,
                "email": known_email,
                "opening_hours": known_hours,
                "error": str(e),
            }

    return {
        "source": "ai-generic",
        "equipment": [],
        "classes": [],
        "phone": known_phone,
        "email": known_email,
        "opening_hours": known_hours,
        "error": str(last_error),
    }
