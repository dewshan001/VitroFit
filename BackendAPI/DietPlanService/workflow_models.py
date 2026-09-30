# DietPlanService/workflow_models.py
"""One new table backing the 3-agent workflow: a durable, traceable record of
every generate-plan run (plan, per-step results, events, validation, approval).
Added via the same Base.metadata.create_all pattern main.py already uses for
diet_plan_inputs/diet_plans - no ALTER, no migrations.
"""
import uuid

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func

from db import Base


class DietWorkflow(Base):
    """A single run of the diet-plan agent workflow, one row per /generate call."""

    __tablename__ = "diet_workflows"

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

    # pending | auto_approved | approved | rejected
    approval_status = Column(String(20), nullable=True)
    approved_by = Column(Integer, nullable=True)
    approval_note = Column(String(1000), nullable=True)

    final_outcome = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)

    # Loose reference to diet_plans.id, set once the workflow's plan is
    # confirmed/persisted. No FK constraint - purely informational, avoids
    # ORM relationship/cascade complexity for a field set once, post-hoc.
    plan_id = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
