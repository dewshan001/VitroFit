# GymAgentService/models.py
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from db import Base


class GymDetails(Base):
    """Cached equipment/classes for a gym, keyed by its map-provider place id.

    `source` tracks how trustworthy the equipment/classes fields are:
      - "verified"    : approved by a Gym_Owner/Admin through a workflow; never overwritten by AI
      - "ai-scraped"   : extracted by the LLM from the gym's own website
      - "ai-inferred"  : the LLM's best guess from partial data
      - "ai-generic"   : the LLM's best guess with no website to read (low confidence)

    A row can only be `verified` if `verified_workflow_id` points at the workflow whose
    approval promoted it. The CHECK constraint makes the database refuse anything else.
    """

    __tablename__ = "gym_agent_details"
    __table_args__ = (
        CheckConstraint(
            "source <> 'verified' OR verified_workflow_id IS NOT NULL",
            name="ck_gym_details_verified_has_workflow",
        ),
    )

    place_id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    website = Column(String(500), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    opening_hours = Column(String(255), nullable=True)

    source = Column(String(20), nullable=False, default="ai-generic")
    equipment = Column(JSON, nullable=False, default=list)
    classes = Column(JSON, nullable=False, default=list)

    # Provenance of a `verified` row: which approved workflow, who approved, and when.
    # RESTRICT: a workflow that vouches for published data cannot be deleted.
    verified_workflow_id = Column(
        String(36),
        ForeignKey("gym_agent_workflows.id", ondelete="RESTRICT", name="fk_gym_details_verified_workflow"),
        nullable=True,
    )
    verified_by = Column(String(100), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class GymWorkoutSuggestions(Base):
    """Cached AI-suggested workouts for a gym, keyed by place id.

    `equipment_fingerprint` is a hash of the equipment/classes list the suggestions
    were generated from — if a gym's known equipment/classes change, the fingerprint
    no longer matches and the cache is regenerated instead of served stale.
    """

    __tablename__ = "gym_agent_workouts"

    place_id = Column(String(255), primary_key=True)
    equipment_fingerprint = Column(String(64), nullable=False)
    workouts = Column(JSON, nullable=False, default=list)
    notes = Column(String(500), nullable=True)

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


_JSON = JSON().with_variant(JSONB(), "postgresql")

WORKFLOW_STATUSES = ("Running", "AwaitingApproval", "Published", "Rejected", "Failed")
APPROVAL_STATUSES = ("none", "pending", "approved", "rejected", "revision_requested")


class GymWorkflow(Base):
    """Durable state of one multi-agent gym workflow run.

    Holds structured state and execution summaries only. No prompts, hidden
    reasoning, tokens or secrets are stored (spec section 6).
    """

    __tablename__ = "gym_agent_workflows"
    __table_args__ = (
        CheckConstraint(
            "status IN ('Running','AwaitingApproval','Published','Rejected','Failed')",
            name="ck_gym_workflow_status",
        ),
        CheckConstraint(
            "approval_status IN ('none','pending','approved','rejected','revision_requested')",
            name="ck_gym_workflow_approval",
        ),
        Index("ix_gym_workflow_status_created", "status", "created_at"),
    )

    id = Column(String(36), primary_key=True)
    place_id = Column(String(255), nullable=False, index=True)
    requested_by = Column(String(100), nullable=False)
    objective = Column(String(500), nullable=False)
    status = Column(String(20), nullable=False, default="Running")

    request = Column(_JSON, nullable=False, default=dict)
    plan = Column(_JSON, nullable=True)
    facts = Column(_JSON, nullable=True)
    recommendations = Column(_JSON, nullable=True)
    validation_results = Column(_JSON, nullable=False, default=list)
    errors = Column(_JSON, nullable=False, default=list)

    approval_status = Column(String(24), nullable=False, default="none")
    approved_by = Column(String(100), nullable=True)
    approver_role = Column(String(30), nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    approval_note = Column(String(500), nullable=True)
    final_outcome = Column(String(500), nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class GymWorkflowStep(Base):
    """One agent/node execution in a workflow (planner, gym_analysis, ..., approval_gate, publish)."""

    __tablename__ = "gym_agent_steps"
    __table_args__ = (
        UniqueConstraint("workflow_id", "seq", name="uq_gym_step_workflow_seq"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(
        String(36), ForeignKey("gym_agent_workflows.id", ondelete="CASCADE"), nullable=False, index=True
    )
    seq = Column(Integer, nullable=False)
    agent = Column(String(40), nullable=False)
    summary = Column(String(300), nullable=True)
    ok = Column(Boolean, nullable=False)
    error = Column(String(100), nullable=True)
    duration_ms = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class GymWorkflowToolCall(Base):
    """One allow-listed tool invocation made by an agent during a step."""

    __tablename__ = "gym_agent_tool_calls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(
        String(36), ForeignKey("gym_agent_workflows.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_id = Column(
        Integer, ForeignKey("gym_agent_steps.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent = Column(String(40), nullable=False)
    tool = Column(String(60), nullable=False)
    input_summary = Column(String(300), nullable=True)
    ok = Column(Boolean, nullable=False)
    error_code = Column(String(60), nullable=True)
    duration_ms = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
