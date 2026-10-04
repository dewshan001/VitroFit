# DietPlanService/src/agent/store.py
"""Persistence helpers for the workflow table that are not plain reads/writes in
the coordinator: the audit-trail mirror and the start-up recovery of runs a
crash left behind.
"""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

from src.models.db_models import DietWorkflow, DietWorkflowStep
from src.utils.logger import log_event

_STEP_ERROR_MAX = 300


@event.listens_for(Session, "before_flush")
def _mirror_events_to_steps(session: Session, flush_context, instances) -> None:
    """Whenever a DietWorkflow's `events` list grew, insert one DietWorkflowStep row per
    new event as part of the SAME flush/commit. Events are append-only, so the rows to
    add are exactly those past the ones already stored."""
    for obj in list(session.new) + list(session.dirty):
        if not isinstance(obj, DietWorkflow) or obj.events is None:
            continue
        if obj.id is None:
            obj.id = uuid.uuid4()  # a new row gets its id at flush; the steps need it now
        stored = 0
        if obj not in session.new:
            stored = session.execute(
                select(func.count(DietWorkflowStep.id)).where(DietWorkflowStep.workflow_id == obj.id)
            ).scalar_one()
        for seq, ev in enumerate(obj.events[stored:], start=stored):
            session.add(DietWorkflowStep(
                workflow_id=obj.id,
                seq=seq,
                step=ev.get("step"),
                agent=str(ev.get("agent", ""))[:60],
                tool=(str(ev["tool"])[:60] if ev.get("tool") else None),
                ok=bool(ev.get("ok", True)),
                error=(str(ev["error"])[:_STEP_ERROR_MAX] if ev.get("error") else None),
                duration_ms=ev.get("duration_ms"),
                guard_flags=ev.get("guard_flags"),
            ))


def fail_stale(session: Session, max_age_seconds: int) -> int:
    """Recover runs a crash or restart left in 'running'. Nothing is executing them any
    more, so they would otherwise stay 'running' forever (and the UI would poll forever).

    - a first generation that never finished -> 'failed' with a plain-language reason;
    - an edit (refine) that never finished -> back to 'completed', plan unchanged, with a note.
    `max_age_seconds` > 0 only recovers rows untouched for that long (several instances sharing a
    database); 0 recovers every 'running' row. Returns how many rows were recovered."""
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=max_age_seconds)
    stale = session.query(DietWorkflow).filter(DietWorkflow.status == "running").all()
    recovered = 0
    for wf in stale:
        touched = wf.updated_at or wf.created_at
        # max_age_seconds == 0 means "nothing in this process is running": recover every row,
        # without comparing clocks (the database's and Python's can differ by a few milliseconds).
        if max_age_seconds > 0 and touched is not None:
            if touched.tzinfo is None:
                touched = touched.replace(tzinfo=timezone.utc)
            if touched > cutoff:
                continue  # still plausibly running
        if wf.final_outcome:
            # Finished once already, so this was an edit that got interrupted: keep the plan.
            wf.status = "completed"
            wf.error = "Your last change was interrupted and wasn't applied. Your plan is unchanged."
        else:
            wf.status = "failed"
            wf.error = "This run was interrupted by a service restart. Please try again."
        recovered += 1
    if recovered:
        session.commit()
        log_event("recovered interrupted workflows", count=recovered)
    return recovered
