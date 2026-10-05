# DietPlanService/src/utils/logger.py
"""Structured, safe logging for the diet-plan workflow.

One line per event, for operators, carrying the workflow id when there is one.
Log lines are trusted output, so they must never carry attacker-controlled or
sensitive text:
  - prompts and model replies are never logged;
  - every value goes through safe(): control characters and newlines removed
    (no log injection), secrets redacted, non-ASCII replaced (safe on any
    console), and truncated.
Level: DIET_LOG_LEVEL (default INFO).
"""
import logging
import os
import re
from typing import Any

logger = logging.getLogger("diet_agent")


def _configure_logger() -> None:
    """Idempotent: safe to import from several modules."""
    level = getattr(logging, os.getenv("DIET_LOG_LEVEL", "INFO").upper(), logging.INFO)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [diet_agent] %(message)s"))
        logger.addHandler(handler)


_configure_logger()

MAX_VALUE_LENGTH = 160

_SECRET = re.compile(
    r"(?i)(sk-[a-z0-9_\-]{8,}|nvapi-[a-z0-9_\-]{8,}|"
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


def log_event(event: str, workflow_id: Any = None, level: int = logging.INFO, **fields: Any) -> None:
    """e.g. `tool end wf=1a2b3c4d agent=MealGeneratorAgent tool=generate_meals ok=True ms=1830`."""
    parts = [safe(event, 60)]
    if workflow_id:
        parts.append(f"wf={safe(str(workflow_id)[:8], 12)}")
    parts.extend(f"{safe(k, 30)}={safe(v)}" for k, v in fields.items())
    logger.log(level, " ".join(parts))
