"""Helpers shared by the LLM-backed agents: bounded retries, timeouts, untrusted text."""

import asyncio
import json
import logging
import os
import re
from typing import Awaitable, Callable, TypeVar

import openai

from src.utils.injection_guard import escape_for_fence

logger = logging.getLogger("gym_agent")

MAX_RETRIES = int(os.getenv("AGENT_MAX_RETRIES", "2"))
RETRY_BACKOFF_SECONDS = float(os.getenv("AGENT_RETRY_BACKOFF", "1.5"))
LLM_TIMEOUT_SECONDS = float(os.getenv("AGENT_LLM_TIMEOUT", "60"))

T = TypeVar("T")

TRANSIENT_ERRORS = (
    openai.APIConnectionError,
    openai.RateLimitError,
    openai.InternalServerError,
    asyncio.TimeoutError,
)


class AgentOutputError(Exception):
    """The model's output could not be parsed into the agent's output contract."""


async def with_retries(call: Callable[[], Awaitable[T]], *, what: str) -> T:
    """Run `call`, retrying transient provider errors a bounded number of times."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            return await asyncio.wait_for(call(), timeout=LLM_TIMEOUT_SECONDS)
        except TRANSIENT_ERRORS as exc:
            logger.warning("Transient error in %s (attempt %d/%d): %s", what, attempt + 1, MAX_RETRIES + 1, type(exc).__name__)
            if attempt == MAX_RETRIES:
                raise
            await asyncio.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
    raise RuntimeError("unreachable")


def untrusted(text: str) -> str:
    """Fence external text so the model treats it as data, not instructions.

    Angle brackets inside the text are replaced, so nothing in it can ever write a closing tag and
    step out of the fence (however it is spelled or obfuscated).
    """
    return f"<untrusted_source>\n{escape_for_fence(text)}\n</untrusted_source>"


def parse_json_object(raw: str) -> dict:
    """Extract the first JSON object from a plain-text model reply.

    Reasoning blocks (<think>...</think>) and markdown code fences are removed first, so braces
    inside them are not mistaken for the answer."""
    raw = re.sub(r"<think>.*?</think>", "", raw or "", flags=re.DOTALL | re.IGNORECASE)
    raw = re.sub(r"```(?:json)?", "", raw, flags=re.IGNORECASE)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise AgentOutputError("no JSON object in model output")
    try:
        data = json.loads(match.group())
    except json.JSONDecodeError as exc:
        raise AgentOutputError("model output is not valid JSON") from exc
    if not isinstance(data, dict):
        raise AgentOutputError("model output JSON is not an object")
    return data
