"""Persistence for gym workflows: state rows, audit events, and the publish step.

All methods are synchronous (SQLAlchemy); async callers wrap them in
asyncio.to_thread. `publish` writes the approved facts + workouts and closes the
workflow in ONE transaction, so an approved run is either fully published or not at all.
"""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update

from src.models.contracts import APPROVER_ROLES
from src.utils.db import SessionLocal
from src.models.db_models import (
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


class PublishRefused(Exception):
    """publish() was asked to promote data that no recorded approval covers."""


def clean_text(value):
    """PostgreSQL text and JSONB cannot hold NUL. Untrusted strings (model output, OSM data, tool
    arguments) can, so every value is cleaned before it is stored, however deeply it is nested."""
    if isinstance(value, str):
        return value.replace("\x00", "")
    if isinstance(value, dict):
        return {clean_text(k): clean_text(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_text(v) for v in value]
    return value


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
        "flags": row.guard_flags,
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
                    place_id=clean_text(request["place_id"]),
                    requested_by=clean_text(requested_by),
                    objective=clean_text(request["objective"]),
                    status="Running",
                    request=clean_text(request),
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
                setattr(row, key, _decided_at(delta[key]) if key == "decided_at" else clean_text(delta[key]))
        for key in LIST_COLUMNS:
            if delta.get(key):
                setattr(row, key, list(getattr(row, key) or []) + clean_text(list(delta[key])))

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
                summary=clean_text(summary or "")[:300] or None,
                ok=ok,
                error=clean_text(error),
                duration_ms=duration_ms,
            )
            s.add(step)
            s.flush()
            for rec in tool_calls:
                s.add(
                    GymWorkflowToolCall(
                        workflow_id=workflow_id,
                        step_id=step.id,
                        agent=clean_text(rec["agent"]),
                        tool=clean_text(rec["tool"]),
                        input_summary=clean_text(rec.get("input") or "")[:300] or None,
                        ok=rec["ok"],
                        error_code=clean_text(rec.get("error")),
                        guard_flags=clean_text(rec.get("flags") or "")[:200] or None,
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
                        flags=c.guard_flags,
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
                    flags=None,
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

    def publish(self, workflow_id: str) -> None:
        """Promote a workflow's data to 'verified' and close it, atomically.

        This is the ONLY code that writes source='verified'. It does not trust its caller:
        inside the transaction it locks the workflow row and refuses unless that row itself
        records an approval by an approver role. It publishes exactly the request, facts and
        workouts stored on that row, and records who approved and which workflow vouches for
        the data (the database CHECK constraint requires that link).
        """
        with SessionLocal() as s, s.begin():
            wf = s.execute(
                select(GymWorkflow).where(GymWorkflow.id == workflow_id).with_for_update()
            ).scalar_one_or_none()
            if wf is None:
                raise PublishRefused("workflow does not exist")
            if wf.status == "Published":
                raise PublishRefused("workflow is already published")
            if wf.approval_status != "approved":
                raise PublishRefused(f"workflow approval is '{wf.approval_status}', not 'approved'")
            if wf.approver_role not in APPROVER_ROLES or not wf.approved_by:
                raise PublishRefused("approval was not recorded by an approver role")
            if not wf.facts or not wf.recommendations:
                raise PublishRefused("workflow has no facts or recommendations to publish")

            request, facts, recs = wf.request, wf.facts, wf.recommendations
            if request.get("place_id") != wf.place_id:
                raise PublishRefused("request does not match the workflow's gym")

            equipment, classes = facts["equipment"], facts["classes"]
            decided_at = wf.decided_at or datetime.now(timezone.utc)
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
                verified_workflow_id=wf.id,
                verified_by=wf.approved_by,
                verified_at=decided_at,
            )
            details = s.get(GymDetails, wf.place_id)
            if details is None:
                s.add(GymDetails(place_id=wf.place_id, **fields))
            else:
                for k, v in fields.items():
                    setattr(details, k, v)

            fingerprint = workout_fingerprint(equipment, classes)
            suggestions = s.get(GymWorkoutSuggestions, wf.place_id)
            workouts = recs["workouts"]
            if suggestions is None:
                s.add(
                    GymWorkoutSuggestions(
                        place_id=wf.place_id,
                        equipment_fingerprint=fingerprint,
                        workouts=workouts,
                        notes=recs.get("notes", ""),
                    )
                )
            else:
                suggestions.equipment_fingerprint = fingerprint
                suggestions.workouts = workouts
                suggestions.notes = recs.get("notes", "")

            wf.status = "Published"
            wf.decided_at = decided_at
            wf.final_outcome = "Approved and published as verified gym data."
