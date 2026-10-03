"""Structured, safe logging of every model and tool call (LangChain callback handler).

One line per event, for operators, carrying the workflow id and graph node when there is one.
Log lines are trusted output, so they must never carry attacker-controlled or sensitive text:
  - prompts and model replies are never logged;
  - scraped/search content is never logged (only its length and the guard's flags);
  - every value goes through safe(): control characters and newlines removed (no log injection),
    secrets redacted, non-ASCII replaced (safe on any console), and truncated.
"""

import logging
import os
import re
import time
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger("gym_agent")


def _configure_logger() -> None:
    """Idempotent: safe to import from several modules. Level from GYM_LOG_LEVEL (default INFO)."""
    level = getattr(logging, os.getenv("GYM_LOG_LEVEL", "INFO").upper(), logging.INFO)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [gym_agent] %(message)s"))
        logger.addHandler(handler)


_configure_logger()

MAX_VALUE_LENGTH = 160

_SECRET = re.compile(
    r"(?i)(sk-[a-z0-9_\-]{8,}|nvapi-[a-z0-9_\-]{8,}|tvly-[a-z0-9_\-]{8,}|"
    r"bearer\s+[a-z0-9._\-+/=]{8,}|eyj[a-z0-9_\-]{10,}\.[a-z0-9_\-]{10,}\.[a-z0-9_\-]*|"
    r"(?:api[_-]?key|token|secret|password)\s*[=:]\s*\S+|[a-z0-9+/]{40,}={0,2})"
)
_CONTROL = re.compile("[\x00-\x1f\x7f-\x9f" + chr(0x2028) + chr(0x2029) + "]+")


def safe(value: Any, limit: int = MAX_VALUE_LENGTH) -> str:
    """Make any value safe to put in a log line."""
    text = "" if value is None else str(value)
    text = _SECRET.sub("[redacted]", text)
    text = _CONTROL.sub(" ", text)
    text = text.encode("ascii", "replace").decode("ascii")
    text = re.sub(r" {2,}", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _context(metadata: dict | None) -> str:
    metadata = metadata or {}
    parts = []
    if metadata.get("workflow_id"):
        parts.append(f"wf={safe(str(metadata['workflow_id'])[:8], 12)}")
    if metadata.get("langgraph_node"):
        parts.append(f"node={safe(metadata['langgraph_node'], 40)}")
    return " ".join(parts) or "wf=-"


def _tool_input_summary(name: str, inputs: Any) -> str:
    """What the tool was asked, in a few safe words: a URL's host and path, or a short query."""
    if not isinstance(inputs, dict):
        return ""
    url = inputs.get("url")
    if isinstance(url, str) and url:
        try:
            parsed = urlparse(url if "://" in url else f"https://{url}")
            return safe(f"{parsed.hostname or ''}{parsed.path or ''}", 80)   # no query string: may hold tokens
        except ValueError:
            return "unparseable-url"
    for key in ("query", "gym_name"):
        if isinstance(inputs.get(key), str):
            return safe(inputs[key], 80)
    return ""


class GymAgentLoggingHandler(BaseCallbackHandler):
    """Attached to the model in llm_config.get_llm() and to every tool call in tool_registry."""

    # A logging problem must never break a workflow.
    raise_error = False

    def __init__(self) -> None:
        # run_id -> (start time, log context). LangChain hands metadata to *_start events only,
        # so the context is remembered for the matching end/error event.
        self._runs: dict[UUID, tuple[float, str]] = {}

    def _begin(self, run_id: UUID, metadata: dict | None) -> str:
        context = _context(metadata)
        self._runs[run_id] = (time.perf_counter(), context)
        return context

    def _finish(self, run_id: UUID) -> tuple[int, str]:
        """(elapsed ms, context) of the run that started earlier; (-1, 'wf=-') if its start was never seen."""
        started, context = self._runs.pop(run_id, (None, "wf=-"))
        elapsed = int((time.perf_counter() - started) * 1000) if started is not None else -1
        return elapsed, context

    # -- models ---------------------------------------------------------

    def on_chat_model_start(self, serialized, messages, *, run_id, metadata=None, **kwargs) -> None:
        # Overridden on purpose: the default falls back to on_llm_start with the full prompt text.
        context = self._begin(run_id, metadata)
        params = kwargs.get("invocation_params") or {}
        model = params.get("model") or params.get("model_name")
        logger.info("llm start %s model=%s", context, safe(model or "unknown", 60))

    def on_llm_start(self, serialized, prompts, *, run_id, metadata=None, **kwargs) -> None:
        context = self._begin(run_id, metadata)
        params = kwargs.get("invocation_params") or {}
        logger.info("llm start %s model=%s", context, safe(params.get("model") or "unknown", 60))

    def on_llm_end(self, response, *, run_id, **kwargs) -> None:
        usage = {}
        try:
            usage = (response.llm_output or {}).get("token_usage") or {}
            if not usage:
                message = response.generations[0][0].message
                usage = getattr(message, "usage_metadata", None) or {}
        except (AttributeError, IndexError, TypeError):
            pass
        tokens = usage.get("total_tokens") or usage.get("total") or "?"
        elapsed, context = self._finish(run_id)
        logger.info("llm end %s ms=%s tokens=%s", context, elapsed, safe(tokens, 12))

    def on_llm_error(self, error, *, run_id, **kwargs) -> None:
        # Type only: provider error bodies can echo prompts or contain keys.
        elapsed, context = self._finish(run_id)
        logger.warning("llm error %s ms=%s type=%s", context, elapsed, type(error).__name__)

    # -- tools ----------------------------------------------------------

    def on_tool_start(self, serialized, input_str, *, run_id, metadata=None, inputs=None, **kwargs) -> None:
        context = self._begin(run_id, metadata)
        name = (serialized or {}).get("name") or kwargs.get("name") or "unknown"
        logger.info("tool start %s tool=%s input=%s", context, safe(name, 40), _tool_input_summary(name, inputs))

    def on_tool_end(self, output, *, run_id, **kwargs) -> None:
        # Length only: the content is untrusted and may be hostile.
        length = len(output) if isinstance(output, str) else len(str(output))
        elapsed, context = self._finish(run_id)
        logger.info("tool end %s ms=%s chars=%d", context, elapsed, length)

    def on_tool_error(self, error, *, run_id, **kwargs) -> None:
        elapsed, context = self._finish(run_id)
        logger.warning("tool error %s ms=%s type=%s", context, elapsed, type(error).__name__)


_HANDLER: GymAgentLoggingHandler | None = None


def get_handler() -> GymAgentLoggingHandler:
    """One shared handler (it only keeps start times keyed by run id)."""
    global _HANDLER
    if _HANDLER is None:
        _HANDLER = GymAgentLoggingHandler()
    return _HANDLER
