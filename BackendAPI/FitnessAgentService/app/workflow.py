"""Explicit LangGraph delegation with durable step summaries in ASP.NET/PostgreSQL.

The agent prepares a self-guided four-week beginner program; instructor-led training starts afterward.
"""
from time import monotonic
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from . import llm
from .rules import prepare_plan, progress_guidance, validate_plan
from .schemas import GenerateRequest, GenerateResult, Plan, Trace
from .tools import call_tool


class State(TypedDict, total=False):
    request: dict
    steps: list[str]
    guidance: str
    plan: dict | None
    errors: list[str]
    attempt: int
    status: str
    toolResults: dict


async def execute(request: GenerateRequest, record, proposer=llm.propose, checkpointer=None) -> GenerateResult:
    async def traced(name, action, state):
        started = monotonic()
        result, summary = await action(state)
        # Fail closed if audit persistence fails. Never produce an unaudited success.
        snapshot = {key: value for key, value in {**state, **result}.items() if key != "request"}
        if isinstance(snapshot.get("plan"), Plan):
            snapshot["plan"] = snapshot["plan"].model_dump()
        await record(Trace(step=name, summary=summary, snapshot=snapshot,
                           durationMs=int((monotonic() - started) * 1000)))
        return result

    async def coordinate(state):
        steps = ["screening", "progress_analyst", "planner", "validator"]
        return {"steps": steps, "attempt": 0, "errors": [], "plan": None}, "Delegate: " + " -> ".join(steps)

    async def screen(state):
        blocked = request.profile.reviewRequired or any(p.pain for p in request.progress)
        return {"status": "ReviewRequired" if blocked else "Planning"}, (
            "Professional review required; automated planning stopped" if blocked else
            "No declared review flag; this is not medical clearance"
        )

    async def analyze(state):
        history = call_tool("progress_analyst", "progress_history", request)
        guidance = progress_guidance(request)
        return {"guidance": guidance, "toolResults": {"progress_history": history}}, "Tool progress_history; " + guidance

    async def plan(state):
        exercises = call_tool("planner", "exercise_search", request)
        try:
            draft = await proposer(request, exercises, state["guidance"], state["errors"])
            prepared = prepare_plan(draft, request)
            return {"plan": prepared.model_dump(mode="json"), "attempt": state["attempt"] + 1,
                    "toolResults": {**state.get("toolResults", {}), "exercise_search": [e.model_dump() for e in exercises]}}, "Tool exercise_search; structured draft matched to approved exercises for each focus"
        except Exception as exc:
            # Do not log raw provider responses, prompts or secrets.
            code = str(exc) if isinstance(exc, llm.PlannerError) else "MODEL_OUTPUT_OR_SERVICE_ERROR"
            return {"plan": None, "errors": [code], "attempt": state["attempt"] + 1}, f"Planner failed: {code}"

    async def validate(state):
        errors = validate_plan(Plan.model_validate(state["plan"]), request) if state["plan"] else state["errors"]
        status = "Ready" if not errors else ("Failed" if state["attempt"] >= 3 else "Planning")
        summary = "Beginner schedule validated and ready" if not errors else "Validation failed: " + "; ".join(errors)
        return {"errors": errors, "status": status}, summary

    graph = StateGraph(State)
    for name, action in [("coordinator", coordinate), ("screening", screen),
                         ("progress_analyst", analyze), ("planner", plan), ("validator", validate)]:
        async def node(state, name=name, action=action):
            return await traced(name, action, state)
        graph.add_node(name, node)
    graph.add_edge(START, "coordinator")
    graph.add_edge("coordinator", "screening")
    graph.add_conditional_edges("screening", lambda s: END if s["status"] == "ReviewRequired" else "progress_analyst")
    graph.add_edge("progress_analyst", "planner")
    graph.add_edge("planner", "validator")
    graph.add_conditional_edges("validator", lambda s: "planner" if s["status"] == "Planning" else END)
    config = {"configurable": {"thread_id": str(request.runId)}, "recursion_limit": 20}
    state = await graph.compile(checkpointer=checkpointer).ainvoke({"request": request.model_dump(mode="json")}, config)
    result_plan = Plan.model_validate(state["plan"]) if state.get("plan") else None
    return GenerateResult(status=state["status"], plan=result_plan if state["status"] == "Ready" else None,
                          errors=state.get("errors", []), analysis=state.get("guidance", ""))
