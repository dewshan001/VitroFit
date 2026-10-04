# DietPlanService/src/models/db_models.py
"""All SQLAlchemy tables: the user-confirmed plans (diet_plan_inputs, diet_plans) and
the durable, traceable record of every generate-plan run (diet_workflows: plan,
per-step results, events, validation, approval).
"""
import uuid

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, ForeignKey, Text, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func

from src.utils.db import Base


class DietPlanInputs(Base):
    """The raw preferences a user submitted for one plan generation, kept as a
    record of what produced the linked DietPlan - saved only once the user
    confirms the resulting plan, not on every /generate call."""

    __tablename__ = "diet_plan_inputs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)

    age = Column(Integer, nullable=False)
    gender = Column(String(20), nullable=False)
    height_cm = Column(Float, nullable=False)
    weight_kg = Column(Float, nullable=False)
    activity_level = Column(String(20), nullable=False)
    goal = Column(String(30), nullable=False)
    meal_frequency = Column(String(20), nullable=False)
    restrictions = Column(JSON, nullable=False, default=list)
    dislikes = Column(String(1000), nullable=True)
    budget_tier = Column(String(20), nullable=False)
    budget_custom_amount = Column(Float, nullable=True)
    medical_conditions = Column(JSON, nullable=False, default=list)
    cooking_time = Column(String(20), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DietPlan(Base):
    """A user-confirmed diet plan, linked back to the inputs that generated it."""

    __tablename__ = "diet_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    inputs_id = Column(Integer, ForeignKey("diet_plan_inputs.id"), nullable=False)

    total_calories = Column(Integer, nullable=False)
    macros = Column(JSON, nullable=False)
    meals = Column(JSON, nullable=False)
    within_tolerance = Column(Boolean, nullable=False, default=True)

    # approved | pending. A high-risk plan is saved as `pending` the moment it is
    # generated and its content stays hidden from the customer until a reviewer
    # approves it (a rejected plan is deleted). Every other plan is `approved`.
    approval_status = Column(String(20), nullable=False, default="approved", server_default="approved")

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DietWorkflow(Base):
    """A single run of the diet-plan agent workflow, one row per /generate call."""

    __tablename__ = "diet_workflows"
    __table_args__ = (
        CheckConstraint("status IN ('running','completed','failed','rejected')", name="ck_diet_workflows_status"),
        CheckConstraint(
            "approval_status IS NULL OR approval_status IN ('pending','auto_approved','approved','rejected')",
            name="ck_diet_workflows_approval_status",
        ),
        CheckConstraint("risk_level IS NULL OR risk_level IN ('low','medium','high')", name="ck_diet_workflows_risk_level"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, nullable=False, index=True)
    objective = Column(String(255), nullable=False)

    # running | completed | failed | rejected
    status = Column(String(20), nullable=False, default="running")

    plan = Column(JSON, nullable=True)
    completed_steps = Column(JSON, nullable=False, default=list)
    inputs = Column(JSON, nullable=False)
    targets = Column(JSON, nullable=True)
    meals = Column(JSON, nullable=True)
    validation_results = Column(JSON, nullable=True)
    events = Column(JSON, nullable=False, default=list)

    # low | medium | high
    risk_level = Column(String(10), nullable=True)

    # standard | medical_review - chosen by the planner
    route = Column(String(20), nullable=True)

    # pending | auto_approved | approved | rejected
    approval_status = Column(String(20), nullable=True)
    approved_by = Column(Integer, nullable=True)
    approver_role = Column(String(20), nullable=True)
    approval_note = Column(String(1000), nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)

    final_outcome = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)

    # Loose reference to diet_plans.id, set once the workflow's plan is
    # confirmed/persisted. No FK constraint - purely informational, avoids
    # ORM relationship/cascade complexity for a field set once, post-hoc.
    plan_id = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DietWorkflowStep(Base):
    """One row per agent/tool step of a run - a queryable audit trail alongside the
    workflow's `events` JSON. Rows are written by src/agent/store.py in the same
    transaction as the workflow update they belong to, so the two can never disagree.
    No prompts, model replies or user text are stored: only which tool ran, whether
    it succeeded, how long it took and any input-guard signal codes."""

    __tablename__ = "diet_workflow_steps"
    __table_args__ = (UniqueConstraint("workflow_id", "seq", name="uq_diet_workflow_steps_workflow_seq"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(PG_UUID(as_uuid=True), ForeignKey("diet_workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    seq = Column(Integer, nullable=False)
    step = Column(Integer, nullable=True)
    agent = Column(String(60), nullable=False)
    tool = Column(String(60), nullable=True)
    ok = Column(Boolean, nullable=False, default=True)
    error = Column(String(300), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    guard_flags = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
