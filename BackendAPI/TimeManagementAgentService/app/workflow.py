from time import monotonic
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from . import llm
from .schemas import GenerateRequest, GenerateResult, Timetable, Trace

class State(TypedDict, total=False):
    request: dict
    steps: list[str]
    timetable: dict | None
    longTermImpact: str
    errors: list[str]
    attempt: int
    status: str

async def execute(request: GenerateRequest, record, proposer=llm.propose_timetable, analyst=llm.analyze_impact, checkpointer=None) -> GenerateResult:
    async def traced(name, action, state):
        started = monotonic()
        result, summary = await action(state)
        snapshot = {key: value for key, value in {**state, **result}.items() if key != "request"}
        if isinstance(snapshot.get("timetable"), Timetable):
            snapshot["timetable"] = snapshot["timetable"].model_dump()
        await record(Trace(step=name, summary=summary, snapshot=snapshot,
                           durationMs=int((monotonic() - started) * 1000)))
        return result

    async def coordinate(state):
        steps = ["scheduler", "analyst", "validator"]
        return {"steps": steps, "attempt": 0, "errors": [], "timetable": None, "longTermImpact": ""}, "Delegate: " + " -> ".join(steps)

    async def schedule(state):
        try:
            draft = await proposer(request, state.get("errors", []))
            return {"timetable": draft.model_dump(mode="json"), "attempt": state["attempt"] + 1}, "Scheduled workouts"
        except Exception as exc:
            import traceback
            traceback.print_exc()
            return {"timetable": None, "errors": [str(exc)], "attempt": state["attempt"] + 1}, f"Scheduler failed: {exc}"

    async def analyze(state):
        try:
            impact = await analyst(request, state.get("timetable"))
            return {"longTermImpact": impact}, "Analyzed long-term impact"
        except Exception as exc:
            return {"longTermImpact": ""}, f"Analyst failed: {exc}"

    async def validate(state):
        errors = []
        if state.get("timetable"):
            tt = Timetable.model_validate(state["timetable"])
            # simple validation: no empty slots
            if not tt.slots:
                errors.append("Timetable has no slots")
        else:
            errors = state.get("errors", ["Missing timetable"])
            
        status = "Ready" if not errors else ("Failed" if state["attempt"] >= 3 else "Planning")
        summary = "Timetable validated and ready" if not errors else "Validation failed: " + "; ".join(errors)
        return {"errors": errors, "status": status}, summary

    graph = StateGraph(State)
    for name, action in [("coordinator", coordinate), ("scheduler", schedule),
                         ("analyst", analyze), ("validator", validate)]:
        async def node(state, name=name, action=action):
            return await traced(name, action, state)
        graph.add_node(name, node)
    
    graph.add_edge(START, "coordinator")
    graph.add_edge("coordinator", "scheduler")
    graph.add_edge("scheduler", "analyst")
    graph.add_edge("analyst", "validator")
    graph.add_conditional_edges("validator", lambda s: "scheduler" if s["status"] == "Planning" else END)
    
    config = {"configurable": {"thread_id": str(request.runId)}, "recursion_limit": 20}
    state = await graph.compile(checkpointer=checkpointer).ainvoke({"request": request.model_dump(mode="json")}, config)
    
    result_tt = Timetable.model_validate(state["timetable"]) if state.get("timetable") else None
    return GenerateResult(status=state["status"], timetable=result_tt if state["status"] == "Ready" else None,
                          errors=state.get("errors", []), longTermImpact=state.get("longTermImpact", ""))
