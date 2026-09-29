"""Per-agent tool allow-lists and the single guarded entry point for tool calls.

Agents never touch a tool object directly. They call `call_tool(role, name, args)`,
which enforces (in order): role allow-list, plan-level narrowing, input validation,
target guards (scrape only the gym's own site, never internal addresses), a timeout,
and output sanitisation. Failures come back as structured results, never raw
exceptions, except PermissionError, which is a programming/escalation error.

Untrusted content passes the prompt-injection guard in both directions: what the model asks a tool
to search for (a query cannot carry a URL or an encoded blob out of the system) and what the tool
returns (suspicious sentences removed, a hostile source withheld entirely, findings recorded).
"""

import asyncio
import os
import time
from dataclasses import dataclass, field

from pydantic import ValidationError

import injection_guard as guard
import tools as gym_tools
from callbacks import get_handler
from url_policy import host_is_internal, normalise_host

# role -> tool names that role may call. Anything absent means "no tools".
TOOL_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "planner": (),
    "gym_analysis": ("scrape_gym_website", "search_gym_info", "lookup_similar_gyms"),
    "workout_recommendation": ("list_equipment_taxonomy",),
    "validator": (),
}

TOOL_TIMEOUT_SECONDS = float(os.getenv("AGENT_TOOL_TIMEOUT", "20"))
MAX_TOOL_OUTPUT_CHARS = 6000
MAX_ARG_LENGTH = 200
# The free-text arguments the model chooses for each tool (a URL is checked separately, by host).
_FREE_TEXT_ARGS = {"search_gym_info": ("query",), "lookup_similar_gyms": ("gym_name", "city")}

_SOFT_ERROR_PREFIXES = ("Error:", "Web search unavailable", "Database lookup failed")

_REGISTRY = {t.name: t for t in gym_tools.get_all_tools()}


@dataclass
class ToolResult:
    tool: str
    ok: bool
    output: str
    error_code: str | None
    duration_ms: int
    flags: list[str] = field(default_factory=list)   # prompt-injection signals found in the output


def tools_for(role: str, allowed: list[str] | None = None) -> list:
    """LangChain tool objects a role may bind to its model (least privilege)."""
    names = TOOL_PERMISSIONS.get(role, ())
    if allowed is not None:
        names = tuple(n for n in names if n in allowed)
    return [_REGISTRY[n] for n in names]


def sanitize_untrusted_text(text: str, limit: int = MAX_TOOL_OUTPUT_CHARS) -> str:
    """Neutralise external content (see injection_guard). A blocked source comes back empty."""
    return guard.guard_text(text, source="text", limit=limit).text


def _arguments_refused(name: str, args: dict) -> bool:
    """A model steered by a hostile page could smuggle data out inside a search query."""
    for key in _FREE_TEXT_ARGS.get(name, ()):
        value = args.get(key)
        if not isinstance(value, str):
            continue
        if len(value) > MAX_ARG_LENGTH or guard.has_url(value) or guard.looks_like_blob(value):
            return True
        if any(f.strong for f in guard.scan(value)):
            return True
    return False


def _result(
    tool: str, ok: bool, output: str, code: str | None, started: float, flags: list[str] | None = None
) -> ToolResult:
    return ToolResult(tool, ok, output, code, int((time.perf_counter() - started) * 1000), flags or [])


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

    if _arguments_refused(name, args):
        return _result(name, False, "", "INVALID_INPUT", started)

    if name == "scrape_gym_website":
        target_host = normalise_host(args.get("url", ""))
        if not website or target_host != normalise_host(website) or host_is_internal(target_host):
            return _result(name, False, "", "TARGET_NOT_ALLOWED", started)

    try:
        raw = await asyncio.wait_for(
            tool.ainvoke(args, config={"callbacks": [get_handler()]}), timeout=TOOL_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        return _result(name, False, "", "TIMEOUT", started)
    except Exception:
        return _result(name, False, "", "TOOL_ERROR", started)

    raw_text = raw if isinstance(raw, str) else str(raw)
    guarded = guard.guard_text(raw_text, source=name, limit=MAX_TOOL_OUTPUT_CHARS)
    if guarded.blocked:
        # Hostile source: the model never sees any of it.
        return _result(name, False, "", "INJECTION_BLOCKED", started, guarded.flags)
    if raw_text.startswith(_SOFT_ERROR_PREFIXES):
        return _result(name, False, guarded.text, "TOOL_UNAVAILABLE", started, guarded.flags)
    return _result(name, True, guarded.text, None, started, guarded.flags)
