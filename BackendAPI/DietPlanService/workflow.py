# DietPlanService/workflow.py
"""The coordinator: builds a plan, dispatches each step to the right agent
through an allow-listed tool call, runs the revise/reject loop, and saves
workflow state (plan, per-step results, events, validation, approval) after
every step so a DietWorkflow row is always a truthful, resumable record of
what happened.

POST /api/diet/generate calls create_workflow() (fast, synchronous - just
persists the initial row) then schedules execute_workflow() as a detached
asyncio task and returns the workflowId immediately, so the frontend can poll
GET /api/diet/workflows/{id} and show each agent's real progress as it
happens instead of blocking on one long request. execute_workflow() opens its
own DB session (SessionLocal()) rather than reusing the request's, since that
session is closed once the request returns - the task keeps running
independently of the request that started it.
"""
import time
from datetime import datetime, timezone

from agents import (
    NutritionAnalystAgent, NutritionAnalystInput,
    MealGeneratorAgent, MealGeneratorInput,
    SafetyValidatorAgent, SafetyValidatorInput,
)
from db import SessionLocal
from workflow_models import DietWorkflow

# Per-tool timeouts. calculate_targets/assess_risk/lookup_budget/validate_plan
# are pure Python with no I/O, so a short timeout is just a safety net.
# generate_meals wraps meal_agent.generate_meals, which has its own internal
# timeout logic (up to two model attempts, plus one corrective retry on
# tolerance failure - meal_agent._CALL_TIMEOUT_SECONDS = 70s per attempt,
# raised there after measuring the live NVIDIA endpoint this service actually
# uses (meta/llama-3.2-11b-vision-instruct) at 65-118s per successful call.
# Worst case is 3 attempts x 70s = 210s; the timeout below gives it room to
# reach that rather than our wrapper cutting off a call that was still in
# progress and about to succeed.
_DEFAULT_TOOL_TIMEOUT_SECONDS = 10
_TOOL_TIMEOUTS = {
    "generate_meals": 220,
}
_OVERALL_TIME_BUDGET_SECONDS = 230
# 1 retry = 2 total meal-generation attempts (the initial one plus one revise).
_MAX_REVISE_RETRIES = 1

_analyst = NutritionAnalystAgent()
_generator = MealGeneratorAgent()
_validator = SafetyValidatorAgent()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_plan(objective: str, prefs: dict) -> list[dict]:
    """Static, explainable 3-4 step plan - not dynamic re-planning. Adaptation
    is limited to a single note appended when medical conditions are present.
    """
    steps = [
        {"step": 1, "agent": "NutritionAnalystAgent", "tool": "calculate_targets",
         "description": "Compute calorie/macro targets and budget context.", "status": "pending"},
        {"step": 2, "agent": "NutritionAnalystAgent", "tool": "assess_risk",
         "description": "Assess health/safety risk level from age, medical conditions, deficit.", "status": "pending"},
        {"step": 3, "agent": "MealGeneratorAgent", "tool": "generate_meals",
         "description": "Generate a day's meals matching targets and preferences.", "status": "pending"},
        {"step": 4, "agent": "SafetyValidatorAgent", "tool": "validate_plan",
         "description": "Validate meals against targets, restrictions, and medical rules.", "status": "pending"},
    ]
    if prefs.get("medicalConditions"):
        steps[3]["description"] += " (medical_review: extra scrutiny applied due to declared medical conditions.)"
    return steps


async def call_tool(agent, tool: str, payload, events: list, step: int) -> dict:
    """Enforces the agent's allow-list, validates via the agent's own Pydantic
    input model, applies a timeout, and appends a short trace entry. Never logs
    raw prompts, full payloads, or secrets - only which tool ran, whether it
    succeeded, and how long it took.
    """
    import asyncio

    started = time.monotonic()
    if tool not in agent.allowed_tools:
        events.append({
            "ts": _now_iso(), "step": step, "agent": agent.name, "tool": tool,
            "ok": False, "error": f"Tool '{tool}' not permitted for {agent.name}.", "duration_ms": 0,
        })
        return {"ok": False, "data": None, "error": f"Tool '{tool}' not permitted for {agent.name}."}

    timeout = _TOOL_TIMEOUTS.get(tool, _DEFAULT_TOOL_TIMEOUT_SECONDS)
    try:
        result = await asyncio.wait_for(agent.run(payload), timeout=timeout)
        duration_ms = int((time.monotonic() - started) * 1000)
        events.append({"ts": _now_iso(), "step": step, "agent": agent.name, "tool": tool, "ok": True, "error": None, "duration_ms": duration_ms})
        return {"ok": True, "data": result.model_dump(), "error": None}
    except asyncio.TimeoutError:
        duration_ms = int((time.monotonic() - started) * 1000)
        error = f"Tool '{tool}' timed out after {timeout}s."
        events.append({"ts": _now_iso(), "step": step, "agent": agent.name, "tool": tool, "ok": False, "error": error, "duration_ms": duration_ms})
        return {"ok": False, "data": None, "error": error}
    except Exception as e:
        duration_ms = int((time.monotonic() - started) * 1000)
        error = str(e)
        events.append({"ts": _now_iso(), "step": step, "agent": agent.name, "tool": tool, "ok": False, "error": error, "duration_ms": duration_ms})
        return {"ok": False, "data": None, "error": error}


def _sum_calories(meals: list) -> float:
    return sum(item.get("calories", 0) or 0 for meal in meals for item in meal.get("items", []))


def _summarize_violations(violations: list[dict]) -> str:
    revise_violations = [v for v in violations if v["severity"] == "revise"]
    if not revise_violations:
        return "Revise the plan to better match the targets and preferences."
    parts = [v["message"] for v in revise_violations[:5]]
    return "Previous attempt had issues: " + "; ".join(parts) + ". Adjust and retry."


def create_workflow(objective: str, prefs: dict, user_id: int, session) -> DietWorkflow:
    """Persists the initial workflow row and returns immediately - the actual
    step execution happens separately in execute_workflow(), so the caller
    (POST /api/diet/generate) can hand the workflowId back right away.
    """
    plan = build_plan(objective, prefs)
    wf = DietWorkflow(
        user_id=user_id,
        objective=objective,
        status="running",
        plan=plan,
        completed_steps=[],
        inputs=prefs,
        events=[],
        retry_count=0,
    )
    session.add(wf)
    session.commit()
    session.refresh(wf)
    return wf


async def execute_workflow(workflow_id, prefs: dict) -> None:
    """Runs the workflow's steps to completion against its own DB session.
    Meant to run as a detached asyncio task (asyncio.create_task) kicked off
    right after create_workflow() - nothing awaits this function directly in
    production, so it must never let an exception escape without first
    marking the row "failed"; otherwise the row would be stuck in "running"
    forever with no one left to report the error.
    """
    session = SessionLocal()
    wf = None
    try:
        wf = session.get(DietWorkflow, workflow_id)
        if wf is None:
            return
        await _run_steps(wf, prefs, session)
    except Exception as e:
        if wf is not None:
            try:
                wf.status = "failed"
                wf.error = f"Unexpected error: {e}"
                session.commit()
            except Exception:
                session.rollback()
    finally:
        session.close()


async def run_workflow(objective: str, prefs: dict, user_id: int, session) -> DietWorkflow:
    """Convenience wrapper: create + fully run a workflow to completion using
    the caller's own session, then refresh it back into that session. Used by
    tests and anything that wants to await full completion synchronously,
    rather than the production create_workflow()+execute_workflow() split
    used for live progress polling.
    """
    wf = create_workflow(objective, prefs, user_id, session)
    await execute_workflow(wf.id, prefs)
    session.refresh(wf)
    return wf


async def _run_steps(wf: DietWorkflow, prefs: dict, session) -> DietWorkflow:
    events = list(wf.events)
    completed_steps = list(wf.completed_steps)
    deadline = time.monotonic() + _OVERALL_TIME_BUDGET_SECONDS

    def _fail(error: str, final_outcome: dict | None = None):
        wf.status = "failed"
        wf.error = error
        wf.events = events
        wf.completed_steps = completed_steps
        if final_outcome is not None:
            wf.final_outcome = final_outcome
        session.commit()
        session.refresh(wf)
        return wf

    def _deadline_exceeded() -> bool:
        return time.monotonic() > deadline

    # --- Step 1: Nutrition Analyst - calculate_targets + assess_risk -------
    analyst_result = await call_tool(_analyst, "calculate_targets", NutritionAnalystInput(prefs=prefs), events, step=1)
    if not analyst_result["ok"]:
        return _fail(analyst_result["error"])

    analyst_data = analyst_result["data"]
    wf.targets = analyst_data["targets"]
    wf.risk_level = analyst_data["risk_level"]
    completed_steps.append({"step": 1, "agent": "NutritionAnalystAgent", "status": "done"})
    completed_steps.append({"step": 2, "agent": "NutritionAnalystAgent", "status": "done"})
    wf.completed_steps = completed_steps
    wf.events = events
    session.commit()

    if _deadline_exceeded():
        return _fail("Workflow exceeded 90s time budget.")

    # --- Step 3: Meal Generator - generate_meals ----------------------------
    generator_result = await call_tool(
        _generator, "generate_meals",
        MealGeneratorInput(targets=wf.targets, prefs=prefs), events, step=3,
    )
    generator_data = generator_result["data"] or {}
    if not generator_result["ok"] or generator_data.get("error"):
        error = generator_result["error"] or generator_data.get("error") or "Meal generation failed."
        return _fail(error)

    meals = generator_result["data"]["meals"]
    wf.meals = meals
    completed_steps.append({"step": 3, "agent": "MealGeneratorAgent", "status": "done"})
    wf.completed_steps = completed_steps
    wf.events = events
    session.commit()

    if _deadline_exceeded():
        return _fail("Workflow exceeded 90s time budget.")

    # --- Step 4: Safety Validator - validate_plan (+ revise loop) ----------
    step_counter = 4
    while True:
        validator_result = await call_tool(
            _validator, "validate_plan",
            SafetyValidatorInput(meals=meals, targets=wf.targets, prefs=prefs), events, step=step_counter,
        )
        if not validator_result["ok"]:
            return _fail(validator_result["error"])

        validation = validator_result["data"]
        wf.validation_results = validation

        # Human-visible attempt detail (not just an internal ok/error flag),
        # so the frontend can show why a plan was revised/rejected/failed
        # instead of a single generic error line.
        attempt_calories = _sum_calories(meals)
        target_calories = wf.targets.get("totalCalories", 0) if wf.targets else 0
        diff_pct = round(abs(attempt_calories - target_calories) / target_calories * 100) if target_calories else 0
        completed_steps.append({
            "step": step_counter, "agent": "SafetyValidatorAgent", "status": "done",
            "attempt": wf.retry_count + 1,
            "verdict": validation["verdict"],
            "attemptCalories": round(attempt_calories),
            "targetCalories": target_calories,
            "diffPct": diff_pct,
            "violations": validation["violations"][:5],
        })
        wf.completed_steps = completed_steps
        wf.events = events
        session.commit()
        step_counter += 1

        verdict = validation["verdict"]
        if verdict == "pass":
            break
        if verdict == "reject":
            wf.status = "rejected"
            wf.final_outcome = {"reason": "validation_reject", "violations": validation["violations"]}
            wf.events = events
            wf.completed_steps = completed_steps
            session.commit()
            session.refresh(wf)
            return wf

        # verdict == "revise"
        wf.retry_count += 1
        if wf.retry_count > _MAX_REVISE_RETRIES:
            # Soft-degrade rather than hard-fail: a "revise" verdict (as
            # opposed to "reject") means no safety/restriction rule was
            # broken - the meals are usable, just not within the calorie
            # tolerance. The pre-existing /generate behaviour (before this
            # workflow existed) always returned a plan and let
            # withinTolerance=false show a warning banner instead of
            # blocking the user outright; matching that here means retries
            # being exhausted doesn't leave the user with nothing.
            wf.status = "completed"
            wf.final_outcome = {
                "totalCalories": wf.targets["totalCalories"],
                "macros": wf.targets["macros"],
                "withinTolerance": False,
                "note": "Closest attempt after retries - calories didn't land within the usual tolerance.",
            }
            wf.approval_status = "pending" if wf.risk_level == "high" else "auto_approved"
            wf.events = events
            wf.completed_steps = completed_steps
            session.commit()
            session.refresh(wf)
            return wf
        if _deadline_exceeded():
            return _fail("Workflow exceeded 90s time budget.")

        corrective_note = _summarize_violations(validation["violations"])
        regen_result = await call_tool(
            _generator, "generate_meals",
            MealGeneratorInput(targets=wf.targets, prefs=prefs, corrective_note=corrective_note),
            events, step=step_counter,
        )
        completed_steps.append({"step": step_counter, "agent": "MealGeneratorAgent", "status": "done", "retry": wf.retry_count})
        wf.completed_steps = completed_steps
        wf.events = events
        session.commit()
        step_counter += 1

        regen_data = regen_result["data"] or {}
        if not regen_result["ok"] or regen_data.get("error"):
            error = regen_result["error"] or regen_data.get("error") or "Meal generation failed."
            return _fail(error)

        meals = regen_result["data"]["meals"]
        wf.meals = meals
        session.commit()

        if _deadline_exceeded():
            return _fail("Workflow exceeded 90s time budget.")

    # --- Success -------------------------------------------------------
    wf.status = "completed"
    wf.final_outcome = {
        "totalCalories": wf.targets["totalCalories"],
        "macros": wf.targets["macros"],
        "withinTolerance": wf.validation_results.get("verdict") == "pass",
    }
    wf.approval_status = "pending" if wf.risk_level == "high" else "auto_approved"
    session.commit()
    session.refresh(wf)
    return wf
