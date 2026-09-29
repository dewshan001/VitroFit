"""Per-agent tool allow-lists and the single guarded entry point for tool calls.

Agents never touch a tool object directly. They call `call_tool(role, name, args)`,
which enforces (in order): role allow-list, plan-level narrowing, input validation,
target guards (scrape only the gym's own site, never internal addresses), a timeout,
and output sanitisation. Failures come back as structured results, never raw
exceptions, except PermissionError, which is a programming/escalation error.
"""

import asyncio
import ipaddress
import os
import re
import time
from dataclasses import dataclass
from urllib.parse import urlparse

from pydantic import ValidationError

import tools as gym_tools

# role -> tool names that role may call. Anything absent means "no tools".
TOOL_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "planner": (),
    "gym_analysis": ("scrape_gym_website", "search_gym_info", "lookup_similar_gyms"),
    "workout_recommendation": ("list_equipment_taxonomy",),
    "validator": (),
}

TOOL_TIMEOUT_SECONDS = float(os.getenv("AGENT_TOOL_TIMEOUT", "20"))
MAX_TOOL_OUTPUT_CHARS = 6000

_INJECTION_LINE = re.compile(
    r"(ignore|disregard|forget)\b.{0,40}\b(previous|above|prior|all|earlier)\b.{0,40}"
    r"\b(instruction|prompt|rule|message)s?"
    r"|you are now\b|system prompt|new instructions?\s*:|\bassistant\s*:|\bsystem\s*:"
    r"|reveal .{0,30}(key|secret|prompt)",
    re.IGNORECASE,
)
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SOFT_ERROR_PREFIXES = ("Error:", "Web search unavailable", "Database lookup failed")

_REGISTRY = {t.name: t for t in gym_tools.get_all_tools()}


@dataclass
class ToolResult:
    tool: str
    ok: bool
    output: str
    error_code: str | None
    duration_ms: int


def tools_for(role: str, allowed: list[str] | None = None) -> list:
    """LangChain tool objects a role may bind to its model (least privilege)."""
    names = TOOL_PERMISSIONS.get(role, ())
    if allowed is not None:
        names = tuple(n for n in names if n in allowed)
    return [_REGISTRY[n] for n in names]


def sanitize_untrusted_text(text: str, limit: int = MAX_TOOL_OUTPUT_CHARS) -> str:
    """Strip control characters and instruction-like lines from external content."""
    text = _CONTROL_CHARS.sub("", text or "")
    kept = [line for line in text.splitlines() if not _INJECTION_LINE.search(line)]
    return "\n".join(kept)[:limit]


def _host_is_internal(host: str) -> bool:
    if host in ("localhost", "") or host.endswith(".local") or host.endswith(".internal"):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved


def _normalise_host(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


def _result(tool: str, ok: bool, output: str, code: str | None, started: float) -> ToolResult:
    return ToolResult(tool, ok, output, code, int((time.perf_counter() - started) * 1000))


async def call_tool(
    role: str,
    name: str,
    args: dict,
    *,
    allowed: list[str] | None = None,
    website: str | None = None,
) -> ToolResult:
    """Run a tool on behalf of `role`. Raises PermissionError if not allowed."""
    if name not in _REGISTRY or name not in TOOL_PERMISSIONS.get(role, ()):
        raise PermissionError(f"Tool '{name}' is not allowed for role '{role}'")
    if allowed is not None and name not in allowed:
        raise PermissionError(f"Tool '{name}' is not permitted by the plan for this run")

    started = time.perf_counter()
    tool = _REGISTRY[name]

    schema = getattr(tool, "args_schema", None)
    if schema is not None and hasattr(schema, "model_validate"):
        try:
            args = schema.model_validate(args or {}).model_dump()
        except ValidationError:
            return _result(name, False, "", "INVALID_INPUT", started)

    if name == "scrape_gym_website":
        target_host = _normalise_host(args.get("url", ""))
        if not website or target_host != _normalise_host(website) or _host_is_internal(target_host):
            return _result(name, False, "", "TARGET_NOT_ALLOWED", started)

    try:
        raw = await asyncio.wait_for(tool.ainvoke(args), timeout=TOOL_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        return _result(name, False, "", "TIMEOUT", started)
    except Exception:
        return _result(name, False, "", "TOOL_ERROR", started)

    text = sanitize_untrusted_text(raw if isinstance(raw, str) else str(raw))
    if raw.startswith(_SOFT_ERROR_PREFIXES) if isinstance(raw, str) else False:
        return _result(name, False, text, "TOOL_UNAVAILABLE", started)
    return _result(name, True, text, None, started)
