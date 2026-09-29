"""Persistence for gym workflows: state rows, audit events, and the publish step.

All methods are synchronous (SQLAlchemy); async callers wrap them in
asyncio.to_thread. `publish` writes the approved facts + workouts and closes the
workflow in ONE transaction, so an approved run is either fully published or not at all.
"""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update

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
        "gymName": (row.request or {}).get("name"),
        "website": (row.request or {}).get("website"),
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

    @staticmethod
    def _merge(row: GymWorkflow, delta: dict) -> None:
        """Merge a node's state delta onto the row (lists append, scalars replace)."""
        for key in SCALAR_COLUMNS:
            if key in delta:
                setattr(row, key, _decided_at(delta[key]) if key == "decided_at" else delta[key])
        for key in LIST_COLUMNS:
            if delta.get(key):
                setattr(row, key, list(getattr(row, key) or []) + list(delta[key]))

    def apply(self, workflow_id: str, delta: dict) -> None:
        with SessionLocal() as s:
            row = s.get(GymWorkflow, workflow_id)
            if row is not None:
                self._merge(row, delta)
                s.commit()

    def record_node(
        self,
        workflow_id: str,
        agent: str,
        *,
        ok: bool,
        duration_ms: int,
        error: str | None,
        summary: str | None,
        tool_calls: list[dict],
        delta: dict,
    ) -> None:
        """Persist one node run atomically: its step row, its tool-call rows, and the
        workflow state delta. Either all of it is recorded or none, so the audit trail
        can never disagree with the workflow state."""
        with SessionLocal() as s, s.begin():
            seq = (
                s.scalar(
                    select(func.coalesce(func.max(GymWorkflowStep.seq), 0)).where(
                        GymWorkflowStep.workflow_id == workflow_id
                    )
                )
                or 0
            ) + 1
            step = GymWorkflowStep(
                workflow_id=workflow_id,
                seq=seq,
                agent=agent,
                summary=(summary or "")[:300] or None,
                ok=ok,
                error=error,
                duration_ms=duration_ms,
            )
            s.add(step)
            s.flush()
            for rec in tool_calls:
                s.add(
                    GymWorkflowToolCall(
                        workflow_id=workflow_id,
                        step_id=step.id,
                        agent=rec["agent"],
                        tool=rec["tool"],
                        input_summary=(rec.get("input") or "")[:300] or None,
                        ok=rec["ok"],
                        error_code=rec.get("error"),
                        duration_ms=rec["durationMs"],
                    )
                )
            row = s.get(GymWorkflow, workflow_id)
            if row is not None:
                self._merge(row, delta)

    def get(self, workflow_id: str) -> dict | None:
        with SessionLocal() as s:
            row = s.get(GymWorkflow, workflow_id)
            if row is None:
                return None
            steps, calls = self._children(s, workflow_id)
            return workflow_to_dict(
                row, [step_to_dict(x) for x in steps], [tool_call_to_dict(x) for x in calls]
            )

    @staticmethod
    def _children(s, workflow_id: str):
        steps = s.scalars(
            select(GymWorkflowStep)
            .where(GymWorkflowStep.workflow_id == workflow_id)
            .order_by(GymWorkflowStep.seq)
        ).all()
        calls = s.scalars(
            select(GymWorkflowToolCall)
            .where(GymWorkflowToolCall.workflow_id == workflow_id)
            .order_by(GymWorkflowToolCall.id)
        ).all()
        return steps, calls

    def events(self, workflow_id: str) -> list[dict]:
        """Chronological timeline: each step preceded by the tool calls it made."""
        with SessionLocal() as s:
            steps, calls = self._children(s, workflow_id)
            by_step: dict[int, list[GymWorkflowToolCall]] = {}
            for c in calls:
                by_step.setdefault(c.step_id, []).append(c)

            timeline: list[dict] = []

            def add(**item) -> None:
                timeline.append({"id": len(timeline) + 1, **item})

            for step in steps:
                for c in by_step.get(step.id, []):
                    add(
                        agent=c.agent,
                        tool=c.tool,
                        ok=c.ok,
                        durationMs=c.duration_ms,
                        error=c.error_code,
                        inputSummary=c.input_summary,
                        outputSummary=None,
                        createdAt=_iso(c.created_at),
                    )
                add(
                    agent=step.agent,
                    tool=None,
                    ok=step.ok,
                    durationMs=step.duration_ms,
                    error=step.error,
                    inputSummary=None,
                    outputSummary=step.summary,
                    createdAt=_iso(step.created_at),
                )
            return timeline

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
            wf.approver_role = actor.get("actor_role")
            wf.decided_at = datetime.now(timezone.utc)
            wf.approval_note = actor.get("reason") or None
            wf.final_outcome = "Approved and published as verified gym data."
