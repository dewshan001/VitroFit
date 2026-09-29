"""LangGraph orchestration of the four gym agents with a human-approval interrupt.

START -> planner -> gym_analysis -> workout_recommendation -> validator
validator: pass -> approval_gate | revise (bounded) -> gym_analysis/workout_recommendation
           | reject or exhausted -> safe_fail
approval_gate (interrupt): approve -> publish -> END | reject -> END
           | revise -> workout_recommendation (bounded) | unauthorised -> wait again

Every node is wrapped by `traced`, which records an audit event and mirrors the state
delta onto the durable workflow row. If auditing/persistence fails the run fails
closed: no audit trail means no result.
"""

import asyncio
import logging
import operator
import time
from typing import Annotated, Any, Callable

from langgraph.errors import GraphBubbleUp
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import ValidationError
from typing_extensions import TypedDict

from agents import gym_analysis, planner, validator, workout_recommendation
from agents._common import TRANSIENT_ERRORS, AgentOutputError
from contracts import (
    AnalysisInput,
    ApprovalDecision,
    GymFacts,
    Plan,
    PlannerInput,
    RecommendInput,
    Recommendations,
    ValidatorInput,
    Verdict,
)
from store import WorkflowStore

logger = logging.getLogger("gym_agent")

MAX_VALIDATION_REVISIONS = 2
MAX_HUMAN_REVISIONS = 2
APPROVER_ROLES = frozenset({"Gym_Owner", "Admin"})


class GymState(TypedDict, total=False):
    workflow_id: str
    request: dict
    plan: dict
    facts: dict
    recommendations: dict
    verdict: dict
    corpus: list[str]
    feedback_analysis: list[str]
    feedback_recs: list[str]
    revisions: int
    human_revisions: int
    approval: dict
    status: str
    approval_status: str
    final_outcome: str
    retry_count: int
    # Per-node deltas that are appended (and mirrored to the workflow row).
    completed_steps: Annotated[list, operator.add]
    tool_results: Annotated[list, operator.add]
    validation_results: Annotated[list, operator.add]
    errors: Annotated[list, operator.add]


def _error_code(exc: Exception) -> str:
    if isinstance(exc, PermissionError):
        return "TOOL_NOT_ALLOWED"
    if isinstance(exc, TRANSIENT_ERRORS):
        return "MODEL_UNAVAILABLE"
    if isinstance(exc, (AgentOutputError, ValidationError)):
        return "OUTPUT_INVALID"
    return "INTERNAL_ERROR"


def _step(agent: str, summary: str) -> dict:
    return {"agent": agent, "summary": summary[:200]}


def build_graph(
    store: WorkflowStore,
    llm_factory: Callable[..., object],
    checkpointer: Any,
    on_published: Callable[[dict, dict, dict], None] | None = None,
):
    async def io(fn, *args, **kwargs):
        return await asyncio.to_thread(fn, *args, **kwargs)

    def traced(agent: str, fn):
        async def wrapper(state: GymState) -> dict:
            wid = state["workflow_id"]
            started = time.perf_counter()
            try:
                delta = await fn(state)
                error = None
            except GraphBubbleUp:
                raise  # interrupt() must pass through untouched
            except Exception as exc:
                error = _error_code(exc)
                logger.warning("Node %s failed for %s: %s", agent, wid, error)
                delta = {
                    "status": "Failed",
                    "approval_status": "none" if agent != "approval_gate" else "pending",
                    "final_outcome": f"Workflow stopped safely ({error}); nothing was published.",
                    "errors": [{"agent": agent, "code": error}],
                }
            duration = int((time.perf_counter() - started) * 1000)
            for rec in delta.get("tool_results", []):
                await io(
                    store.add_event,
                    wid,
                    rec["agent"],
                    tool=rec["tool"],
                    ok=rec["ok"],
                    duration_ms=rec["durationMs"],
                    error=rec.get("error"),
                    input_summary=rec.get("input"),
                )
            steps = delta.get("completed_steps") or []
            await io(
                store.add_event,
                wid,
                agent,
                ok=error is None,
                duration_ms=duration,
                error=error,
                output_summary=steps[-1]["summary"] if steps else delta.get("final_outcome"),
            )
            await io(store.apply, wid, delta)
            return delta

        return wrapper

    # ── nodes ───────────────────────────────────────────────────────────

    async def planner_node(state: GymState) -> dict:
        plan = planner.run(PlannerInput.model_validate(state["request"]))
        return {
            "plan": plan.model_dump(mode="json"),
            "completed_steps": [_step("planner", f"Plan created: route={plan.route}, {len(plan.steps)} steps")],
        }

    async def gym_analysis_node(state: GymState) -> dict:
        inp = AnalysisInput(
            gym=PlannerInput.model_validate(state["request"]),
            plan=Plan.model_validate(state["plan"]),
            feedback=state.get("feedback_analysis", []),
        )
        facts, corpus, records = await gym_analysis.run(inp, llm_factory)
        return {
            "facts": facts.model_dump(mode="json"),
            "corpus": corpus,
            "tool_results": records,
            "completed_steps": [
                _step(
                    "gym_analysis",
                    f"{len(facts.equipment)} equipment, {len(facts.classes)} classes, "
                    f"confidence {facts.confidence:.2f}, {len(records)} tool calls",
                )
            ],
        }

    async def workout_node(state: GymState) -> dict:
        request = state["request"]
        inp = RecommendInput(
            name=request["name"],
            facts=GymFacts.model_validate(state["facts"]),
            feedback=state.get("feedback_recs", []),
        )
        recs, records = await workout_recommendation.run(inp, llm_factory)
        return {
            "recommendations": recs.model_dump(mode="json"),
            "tool_results": records,
            "completed_steps": [_step("workout_recommendation", f"{len(recs.workouts)} workouts proposed")],
        }

    async def validator_node(state: GymState) -> dict:
        verdict: Verdict = validator.run(
            ValidatorInput(
                gym=PlannerInput.model_validate(state["request"]),
                plan=Plan.model_validate(state["plan"]),
                facts=GymFacts.model_validate(state["facts"]),
                recommendations=Recommendations.model_validate(state["recommendations"]),
                corpus=state.get("corpus", []),
            )
        )
        attempt = state.get("revisions", 0) + 1
        delta: dict = {
            "verdict": verdict.model_dump(mode="json"),
            "revisions": attempt,
            "retry_count": attempt - 1,
            "feedback_analysis": [v.message for v in verdict.violations if v.target == "gym_analysis"],
            "feedback_recs": [v.message for v in verdict.violations if v.target == "workout_recommendation"],
            "validation_results": [
                {
                    "attempt": attempt,
                    "verdict": verdict.verdict,
                    "violations": [v.model_dump(mode="json") for v in verdict.violations],
                }
            ],
            "completed_steps": [
                _step("validator", f"attempt {attempt}: {verdict.verdict}, {len(verdict.violations)} violations")
            ],
        }
        if verdict.verdict == "pass":
            delta.update(status="AwaitingApproval", approval_status="pending")
        return delta

    async def approval_gate_node(state: GymState) -> dict:
        request = state["request"]
        raw = interrupt(
            {
                "workflowId": state["workflow_id"],
                "placeId": request["place_id"],
                "name": request["name"],
                "facts": state["facts"],
                "recommendations": state["recommendations"],
            }
        )
        decision = ApprovalDecision.model_validate(raw)
        summary = f"{decision.decision} by {decision.actor_role} ({decision.actor_id})"
        base = {"approval": decision.model_dump(mode="json")}

        if decision.actor_role not in APPROVER_ROLES:
            return {
                **base,
                "status": "AwaitingApproval",
                "errors": [{"agent": "approval_gate", "code": "UNAUTHORIZED_APPROVER"}],
                "completed_steps": [_step("approval_gate", f"ignored: {summary} is not an approver")],
            }
        if decision.decision == "approve":
            return {
                **base,
                "approval_status": "approved",
                "approved_by": decision.actor_id,
                "approval_note": decision.reason or None,
                "completed_steps": [_step("approval_gate", summary)],
            }
        if decision.decision == "reject":
            return {
                **base,
                "status": "Rejected",
                "approval_status": "rejected",
                "approved_by": decision.actor_id,
                "approval_note": decision.reason or None,
                "final_outcome": "Rejected by reviewer; nothing was published.",
                "completed_steps": [_step("approval_gate", summary)],
            }
        humans = state.get("human_revisions", 0) + 1
        delta = {
            **base,
            "human_revisions": humans,
            "approved_by": decision.actor_id,
            "approval_note": decision.reason or None,
            "completed_steps": [_step("approval_gate", summary)],
        }
        if humans > MAX_HUMAN_REVISIONS:
            delta.update(
                status="Failed",
                approval_status="revision_requested",
                final_outcome="Revision limit reached; nothing was published.",
            )
        else:
            delta.update(
                status="Running",
                approval_status="revision_requested",
                feedback_recs=[decision.reason or "Reviewer requested a revision."],
            )
        return delta

    async def publish_node(state: GymState) -> dict:
        request, facts, recs = state["request"], state["facts"], state["recommendations"]
        approval = state["approval"]
        await io(store.publish, state["workflow_id"], request, facts, recs, approval)
        if on_published is not None:
            try:
                await io(on_published, request, facts, recs)
            except Exception:
                logger.exception("Post-publish indexing failed for %s", request["place_id"])
        return {
            "status": "Published",
            "approval_status": "approved",
            "final_outcome": "Approved and published as verified gym data.",
            "completed_steps": [_step("publish", "Published as verified")],
        }

    async def safe_fail_node(state: GymState) -> dict:
        if state.get("final_outcome"):
            outcome = state["final_outcome"]
        else:
            verdict = state.get("verdict") or {}
            codes = sorted({v["code"] for v in verdict.get("violations", [])})
            outcome = (
                f"Validation {'rejected' if verdict.get('verdict') == 'reject' else 'did not pass'} "
                f"({', '.join(codes) or 'unknown'}); nothing was published."
            )
        return {
            "status": "Failed",
            "final_outcome": outcome,
            "completed_steps": [_step("safe_fail", outcome)],
        }

    # ── routing ─────────────────────────────────────────────────────────

    def or_fail(next_node: str):
        return lambda s: "safe_fail" if s.get("status") == "Failed" else next_node

    def after_validator(s: GymState) -> str:
        if s.get("status") == "Failed":
            return "safe_fail"
        verdict = s["verdict"]
        if verdict["verdict"] == "pass":
            return "approval_gate"
        if verdict["verdict"] == "reject" or s.get("revisions", 0) > MAX_VALIDATION_REVISIONS:
            return "safe_fail"
        if any(v["target"] == "gym_analysis" for v in verdict["violations"]):
            return "gym_analysis"
        return "workout_recommendation"

    def after_approval(s: GymState) -> str:
        if s.get("status") == "Failed":
            return "safe_fail"
        approval = s.get("approval") or {}
        if approval.get("actor_role") not in APPROVER_ROLES:
            return "approval_gate"
        return {"approve": "publish", "reject": END, "revise": "workout_recommendation"}[
            approval["decision"]
        ]

    g = StateGraph(GymState)
    g.add_node("planner", traced("planner", planner_node))
    g.add_node("gym_analysis", traced("gym_analysis", gym_analysis_node))
    g.add_node("workout_recommendation", traced("workout_recommendation", workout_node))
    g.add_node("validator", traced("validator", validator_node))
    g.add_node("approval_gate", traced("approval_gate", approval_gate_node))
    g.add_node("publish", traced("publish", publish_node))
    g.add_node("safe_fail", traced("safe_fail", safe_fail_node))

    g.add_edge(START, "planner")
    g.add_conditional_edges("planner", or_fail("gym_analysis"), ["gym_analysis", "safe_fail"])
    g.add_conditional_edges("gym_analysis", or_fail("workout_recommendation"), ["workout_recommendation", "safe_fail"])
    g.add_conditional_edges("workout_recommendation", or_fail("validator"), ["validator", "safe_fail"])
    g.add_conditional_edges(
        "validator", after_validator, ["approval_gate", "gym_analysis", "workout_recommendation", "safe_fail"]
    )
    g.add_conditional_edges(
        "approval_gate",
        after_approval,
        ["publish", "approval_gate", "workout_recommendation", "safe_fail", END],
    )
    g.add_conditional_edges("publish", or_fail(END), [END, "safe_fail"])
    g.add_edge("safe_fail", END)

    return g.compile(checkpointer=checkpointer)
