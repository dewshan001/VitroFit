from time import monotonic
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from . import llm
from . import injection_guard as guard
from .schemas import GenerateRequest, GenerateResult, Timetable, Trace

class State(TypedDict, total=False):
    request: dict
    steps: list[str]
    timetable: dict | None
    longTermImpact: str
    errors: list[str]
    attempt: int
    status: str

PREFERENCES_LIMIT = 1000
IMPACT_LIMIT = 1000
BLOCKED_MESSAGE = ("Your preferences contain text that looks like an instruction to the AI. "
                   "Please describe your schedule in plain words.")

def unsafe_text(text: str) -> bool:
    """Model output that carries an instruction, a link or markup must not reach a reviewer or the database."""
    return guard.has_markup_or_link(text) or any(f.strong for f in guard.scan(text))

def check_preferences(preferences: str) -> guard.Guarded:
    return guard.guard_field(preferences, source="preferences", limit=PREFERENCES_LIMIT)

async def execute(request: GenerateRequest, record, proposer=llm.propose_timetable, analyst=llm.analyze_impact, checkpointer=None) -> GenerateResult:
    checked = check_preferences(request.preferences)
    if checked.blocked:
        return GenerateResult(status="Failed", errors=[BLOCKED_MESSAGE])
    request = request.model_copy(update={"preferences": checked.text})

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
            if not isinstance(impact, str) or unsafe_text(impact):
                return {"longTermImpact": ""}, "Analyst output withheld by the injection guard"
            return {"longTermImpact": impact[:IMPACT_LIMIT]}, "Analyzed long-term impact"
        except Exception as exc:
            return {"longTermImpact": ""}, f"Analyst failed: {exc}"

    async def validate(state):
        errors = []
        if state.get("timetable"):
            tt = Timetable.model_validate(state["timetable"])
            # simple validation: no empty slots
            if not tt.slots:
                errors.append("Timetable has no slots")
            elif any(unsafe_text(f"{s.focus} {s.description}") for s in tt.slots):
                errors.append("OUTPUT_INJECTION: slot text contains an instruction, link or markup")
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
