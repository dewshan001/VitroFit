"""Persistence for gym workflows: state rows, audit events, and the publish step.

All methods are synchronous (SQLAlchemy); async callers wrap them in
asyncio.to_thread. `publish` writes the approved facts + workouts and closes the
workflow in ONE transaction, so an approved run is either fully published or not at all.
"""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from db import SessionLocal
from models import (
    GymDetails,
    GymWorkflow,
    GymWorkflowStep,
    GymWorkflowToolCall,
    GymWorkoutSuggestions,
)

# State keys whose per-node deltas are appended to a JSON list column.
# (Steps and tool calls are NOT here: they are normalised into their own tables.)
LIST_COLUMNS = ("validation_results", "errors")
# State keys copied as-is onto the workflow row.
SCALAR_COLUMNS = (
    "plan",
    "facts",
    "recommendations",
    "status",
    "approval_status",
    "approved_by",
    "approver_role",
    "decided_at",
    "approval_note",
    "final_outcome",
    "retry_count",
)


def workout_fingerprint(equipment: list[str], classes: list[str]) -> str:
    key = "|".join(sorted(equipment)) + "::" + "|".join(sorted(classes))
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def workflow_to_dict(row: GymWorkflow, steps: list | None = None, tool_calls: list | None = None) -> dict:
    return {
        "id": row.id,
        "placeId": row.place_id,
        "requestedBy": row.requested_by,
        "objective": row.objective,
        "status": row.status,
        "plan": row.plan,
        "completedSteps": steps,
        "toolResults": tool_calls,
        "facts": row.facts,
        "recommendations": row.recommendations,
        "validationResults": row.validation_results or [],
        "errors": row.errors or [],
        "approvalStatus": row.approval_status,
        "approvedBy": row.approved_by,
        "approverRole": row.approver_role,
        "decidedAt": _iso(row.decided_at),
        "approvalNote": row.approval_note,
        "finalOutcome": row.final_outcome,
        "retryCount": row.retry_count,
        "createdAt": _iso(row.created_at),
        "updatedAt": _iso(row.updated_at),
    }


def step_to_dict(row: GymWorkflowStep) -> dict:
    return {
        "id": row.id,
        "seq": row.seq,
        "agent": row.agent,
        "summary": row.summary,
        "ok": row.ok,
        "error": row.error,
        "durationMs": row.duration_ms,
        "createdAt": _iso(row.created_at),
    }


def tool_call_to_dict(row: GymWorkflowToolCall) -> dict:
    return {
        "id": row.id,
        "stepId": row.step_id,
        "agent": row.agent,
        "tool": row.tool,
        "input": row.input_summary,
        "ok": row.ok,
        "error": row.error_code,
        "durationMs": row.duration_ms,
        "createdAt": _iso(row.created_at),
    }


def _decided_at(value):
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return value


class WorkflowStore:
    def create(self, request: dict, requested_by: str) -> str:
        workflow_id = str(uuid.uuid4())
        with SessionLocal() as s:
            s.add(
                GymWorkflow(
                    id=workflow_id,
                    place_id=request["place_id"],
                    requested_by=requested_by,
                    objective=request["objective"],
                    status="Running",
                    request=request,
                    validation_results=[],
                    errors=[],
                    approval_status="none",
                    retry_count=0,
                )
            )
            s.commit()
        return workflow_id

    def apply(self, workflow_id: str, delta: dict) -> None:
        """Merge a node's state delta onto the row (lists append, scalars replace)."""
        with SessionLocal() as s:
            row = s.get(GymWorkflow, workflow_id)
            if row is None:
                return
            for key in SCALAR_COLUMNS:
                if key in delta:
                    setattr(row, key, _decided_at(delta[key]) if key == "decided_at" else delta[key])
            for key in LIST_COLUMNS:
                if delta.get(key):
                    setattr(row, key, list(getattr(row, key) or []) + list(delta[key]))
            s.commit()

    def add_event(
        self,
        workflow_id: str,
        agent: str,
        *,
        tool: str | None = None,
        ok: bool = True,
        duration_ms: int = 0,
        error: str | None = None,
        input_summary: str | None = None,
        output_summary: str | None = None,
    ) -> None:
        with SessionLocal() as s:
            s.add(
                GymWorkflowEvent(
                    workflow_id=workflow_id,
                    agent=agent,
                    tool=tool,
                    ok=ok,
                    duration_ms=duration_ms,
                    error=error,
                    input_summary=(input_summary or "")[:300] or None,
                    output_summary=(output_summary or "")[:300] or None,
                )
            )
            s.commit()

    def get(self, workflow_id: str) -> dict | None:
        with SessionLocal() as s:
            row = s.get(GymWorkflow, workflow_id)
            return workflow_to_dict(row) if row else None

    def events(self, workflow_id: str) -> list[dict]:
        with SessionLocal() as s:
            rows = s.scalars(
                select(GymWorkflowEvent)
                .where(GymWorkflowEvent.workflow_id == workflow_id)
                .order_by(GymWorkflowEvent.id)
            ).all()
            return [event_to_dict(r) for r in rows]

    def list_workflows(
        self, *, status: str | None = None, requested_by: str | None = None, limit: int = 50
    ) -> list[dict]:
        with SessionLocal() as s:
            q = select(GymWorkflow).order_by(GymWorkflow.created_at.desc()).limit(limit)
            if status:
                q = q.where(GymWorkflow.status == status)
            if requested_by:
                q = q.where(GymWorkflow.requested_by == requested_by)
            return [workflow_to_dict(r) for r in s.scalars(q).all()]

    def active_for_place(self, place_id: str) -> bool:
        with SessionLocal() as s:
            return (
                s.scalar(
                    select(GymWorkflow.id)
                    .where(
                        GymWorkflow.place_id == place_id,
                        GymWorkflow.status.in_(("Running", "AwaitingApproval")),
                    )
                    .limit(1)
                )
                is not None
            )

    def claim(self, workflow_id: str, from_status: str, to_status: str) -> bool:
        """Atomic compare-and-swap on status. Stops double approval of one run."""
        with SessionLocal() as s:
            result = s.execute(
                update(GymWorkflow)
                .where(GymWorkflow.id == workflow_id, GymWorkflow.status == from_status)
                .values(status=to_status)
            )
            s.commit()
            return result.rowcount == 1

    def fail_stale(self, older_than_seconds: int) -> int:
        """Mark runs left 'Running' by a crash as Failed (they can never finish)."""
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=older_than_seconds)
        with SessionLocal() as s:
            rows = s.scalars(
                select(GymWorkflow).where(
                    GymWorkflow.status == "Running", GymWorkflow.updated_at < cutoff
                )
            ).all()
            for row in rows:
                row.status = "Failed"
                row.final_outcome = "Interrupted before completion; nothing was published."
                row.errors = list(row.errors or []) + [{"agent": "system", "code": "INTERRUPTED"}]
            s.commit()
            return len(rows)

    def publish(self, workflow_id: str, request: dict, facts: dict, recs: dict, actor: dict) -> None:
        """Write approved data as 'verified' and close the workflow, atomically."""
        equipment, classes = facts["equipment"], facts["classes"]
        with SessionLocal() as s, s.begin():
            details = s.get(GymDetails, request["place_id"])
            fields = dict(
                name=request["name"],
                lat=request.get("lat"),
                lng=request.get("lng"),
                website=request.get("website"),
                phone=request.get("known_phone") or facts.get("phone"),
                email=request.get("known_email") or facts.get("email"),
                opening_hours=request.get("known_hours") or facts.get("opening_hours"),
                source="verified",
                equipment=equipment,
                classes=classes,
            )
            if details is None:
                s.add(GymDetails(place_id=request["place_id"], **fields))
            else:
                for k, v in fields.items():
                    setattr(details, k, v)

            fingerprint = workout_fingerprint(equipment, classes)
            suggestions = s.get(GymWorkoutSuggestions, request["place_id"])
            workouts = recs["workouts"]
            if suggestions is None:
                s.add(
                    GymWorkoutSuggestions(
                        place_id=request["place_id"],
                        equipment_fingerprint=fingerprint,
                        workouts=workouts,
                        notes=recs.get("notes", ""),
                    )
                )
            else:
                suggestions.equipment_fingerprint = fingerprint
                suggestions.workouts = workouts
                suggestions.notes = recs.get("notes", "")

            wf = s.get(GymWorkflow, workflow_id)
            wf.status = "Published"
            wf.approval_status = "approved"
            wf.approved_by = actor["actor_id"]
            wf.approval_note = actor.get("reason") or None
            wf.final_outcome = "Approved and published as verified gym data."
