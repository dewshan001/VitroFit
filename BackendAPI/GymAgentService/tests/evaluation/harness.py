"""Runs one golden case through the real graph, runner, store and validator, and checks the outcome.

Only the outside world is scripted (the model's replies, the tools' web results, the clock's budget).
Everything the assignment wants evidenced (planning, delegation, tool selection, structured output,
validation, business rules, approval enforcement, injection resistance, recovery, safe failure) is
checked here with plain assertions on stored data. No LLM-as-judge.
"""

import asyncio
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

import tool_registry
from contracts import ApprovalDecision, GymFacts, Recommendations
from db import SessionLocal
from models import GymDetails
from runner import Conflict
from store import WorkflowStore
from tests.evaluation.cases import DEFAULT, Case
from tests.support import FakeModel, fake_scrape_tool, fake_search_tool, gym_request
from tests.test_workflow import make_runner


@dataclass
class Outcome:
    workflow_id: str
    row: dict
    steps: list[str]
    tools: dict[str, list[str]]
    tool_errors: set[str]
    flags: set[str]
    codes: set[str]
    verdicts: list[str]
    published: bool
    prompt_text: str
    model_calls: int
    actions: list[str]
    error_codes: set[str]


@dataclass
class Check:
    case_id: str
    criterion: str
    name: str
    expected: Any
    observed: Any
    passed: bool


# ── running a case ──────────────────────────────────────────────────────


def run_case(case: Case, monkeypatch) -> Outcome:
    if case.scrape_text is not None:
        monkeypatch.setitem(tool_registry._REGISTRY, "scrape_gym_website", fake_scrape_tool(case.scrape_text))
    if case.search_text is not None:
        monkeypatch.setitem(tool_registry._REGISTRY, "search_gym_info", fake_search_tool(case.search_text))

    model_args: dict[str, Any] = dict(facts=case.facts, recs=case.recs, fail=case.model_fail, delay=case.delay)
    if case.tool_calls is not DEFAULT:
        model_args["tool_calls"] = case.tool_calls
    model = FakeModel(**model_args)

    async def scenario():
        shared = MemorySaver()                       # stands in for the durable Postgres checkpointer
        runner = make_runner(model, checkpointer=shared, budget=case.budget)
        wid = await runner.start(gym_request(**case.request), "eval-user")
        await runner.drain()

        if case.raw_resume:
            kind, role = case.raw_resume
            decision = ApprovalDecision(decision=kind, reason="golden case", actor_id="intruder", actor_role=role)
            await runner.graph.ainvoke(Command(resume=decision.model_dump(mode="json")), runner._config(wid))

        async def decide(kind: str, role: str) -> str:
            try:
                await runner.decide(wid, ApprovalDecision(decision=kind, reason="golden case", actor_id="reviewer-1", actor_role=role))
                return "applied"
            except PermissionError:
                return "denied"
            except Conflict:
                return "conflict"

        results: list[str] = []
        if case.concurrent_actions:
            results = list(await asyncio.gather(*(decide(kind, role) for kind, role in case.actions)))
            await runner.drain()
            return wid, results

        restarted = False
        for kind, role in case.actions:
            if case.restart_before_actions and not restarted:
                # a brand-new runner, graph and model: only the durable storage carries over
                runner = make_runner(FakeModel(), checkpointer=shared, budget=case.budget)
                await runner.recover()
                restarted = True
            results.append(await decide(kind, role))
            await runner.drain()
        return wid, results

    wid, action_results = asyncio.run(scenario())
    return observe(wid, model, action_results)


def observe(wid: str, model: FakeModel, action_results: list[str]) -> Outcome:
    store = WorkflowStore()
    row = store.get(wid)
    events = store.events(wid)
    tools: dict[str, set[str]] = defaultdict(set)
    for e in events:
        if e["tool"]:
            tools[e["agent"]].add(e["tool"])
    calls = row["toolResults"]
    with SessionLocal() as s:
        details = s.get(GymDetails, row["placeId"])
        published = bool(details and details.source == "verified")
    return Outcome(
        workflow_id=wid,
        row=row,
        steps=[e["agent"] for e in events if not e["tool"]],
        tools={agent: sorted(names) for agent, names in tools.items()},
        tool_errors={c["error"] for c in calls if c["error"]},
        flags={f for c in calls for f in (c["flags"] or "").split(",") if f},
        codes={v["code"] for r in row["validationResults"] for v in r["violations"]},
        verdicts=[r["verdict"] for r in row["validationResults"]],
        published=published,
        prompt_text=model.all_prompt_text().lower(),
        model_calls=len(model.prompts),
        actions=action_results,
        error_codes={e["code"] for e in row["errors"]},
    )


# ── what can be observed, and how it is compared ────────────────────────
# name -> (observer, comparison). Comparisons: eq, subset (expected is contained in observed),
# disjoint (none of expected in observed), absent (no expected string in observed text), contains.

Observer = Callable[[Outcome], Any]

OBSERVERS: dict[str, tuple[Observer, str]] = {
    "route": (lambda o: (o.row["plan"] or {}).get("route"), "eq"),
    "steps": (lambda o: o.steps, "eq"),
    "steps_end_with": (lambda o: o.steps[-1] if o.steps else None, "eq"),
    "tools": (lambda o: o.tools, "eq"),
    "tools_never_used": (lambda o: {t for names in o.tools.values() for t in names}, "disjoint"),
    "verdicts": (lambda o: o.verdicts, "eq"),
    "codes": (lambda o: o.codes, "subset"),
    "retry_count": (lambda o: o.row["retryCount"], "eq"),
    "status": (lambda o: o.row["status"], "eq"),
    "approval_status": (lambda o: o.row["approvalStatus"], "eq"),
    "published": (lambda o: o.published, "eq"),
    "actions": (lambda o: o.actions, "eq"),
    "action_counts": (lambda o: dict(Counter(o.actions)), "eq"),
    "finished": (lambda o: o.row["status"] in ("Published", "Rejected"), "eq"),
    "flags": (lambda o: o.flags, "subset"),
    "tool_errors": (lambda o: o.tool_errors, "subset"),
    "prompt_never_contains": (lambda o: o.prompt_text, "absent"),
    "model_calls": (lambda o: o.model_calls, "eq"),
    "error_codes": (lambda o: o.error_codes, "subset"),
    "outcome_contains": (lambda o: o.row["finalOutcome"] or "", "contains"),
}


def _compare(mode: str, expected: Any, observed: Any) -> tuple[bool, Any]:
    """(passed, what to show as observed)."""
    if mode == "eq":
        return observed == expected, observed
    if mode == "subset":
        return set(expected) <= set(observed), sorted(observed)
    if mode == "disjoint":
        return set(expected).isdisjoint(observed), sorted(observed)
    if mode == "absent":
        found = [s for s in expected if s.lower() in observed]
        return not found, {"found": found}
    if mode == "contains":
        return expected in observed, observed
    raise AssertionError(f"unknown comparison {mode}")


def evaluate(case: Case, outcome: Outcome) -> list[Check]:
    checks: list[Check] = []
    for exp in case.expects:
        observer, mode = OBSERVERS[exp.name]
        passed, shown = _compare(mode, exp.value, observer(outcome))
        checks.append(Check(case.id, exp.criterion, exp.name, exp.value, shown, passed))

    # Structured outputs are checked for every case that produced any: what the agents stored must satisfy
    # their output contracts exactly (unknown fields, wrong types or out-of-range values would fail).
    for label, model, payload in (("facts", GymFacts, outcome.row["facts"]), ("recommendations", Recommendations, outcome.row["recommendations"])):
        if payload is not None:
            try:
                model.model_validate(payload)
                ok, shown = True, "valid"
            except Exception as exc:  # pragma: no cover - only shown when a contract is broken
                ok, shown = False, f"{type(exc).__name__}"
            checks.append(Check(case.id, "structured_outputs", f"{label}_match_contract", "valid", shown, ok))
    return checks
