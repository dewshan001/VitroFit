# BackendAPI/GymAgentService/fitness_agent/models_fitness.py
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from db import Base


class FitnessProfile(Base):
    __tablename__ = "fitness_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    age = Column(Integer, nullable=False)
    height_cm = Column(Float, nullable=False)
    weight_kg = Column(Float, nullable=False)
    fitness_goal = Column(String(100), nullable=False)
    experience_level = Column(String(50), nullable=False, default="Beginner")
    available_days = Column(JSON, nullable=False, default=list)
    session_duration = Column(Integer, nullable=False, default=45)
    selected_gym = Column(String(255), nullable=True)
    health_conditions = Column(JSON, nullable=False, default=list)
    declared_injuries = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ExerciseCatalog(Base):
    __tablename__ = "exercise_catalog"

    id = Column(String(50), primary_key=True)
    name = Column(String(150), nullable=False)
    target_muscle = Column(String(100), nullable=False, index=True)
    difficulty = Column(String(50), nullable=False, default="Beginner")
    equipment = Column(String(100), nullable=False, default="Bodyweight")
    beginner_allowed = Column(Boolean, nullable=False, default=True)
    instructions = Column(Text, nullable=False)
    safety_notes = Column(Text, nullable=True)


class WorkoutPlanEntity(Base):
    __tablename__ = "workout_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(String(100), nullable=False, unique=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    week_number = Column(Integer, nullable=False, default=1)
    title = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="AWAITING_APPROVAL")
    target_experience = Column(String(50), nullable=False, default="Beginner")
    session_duration_minutes = Column(Integer, nullable=False, default=45)
    plan_data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ProgressRecordEntity(Base):
    __tablename__ = "progress_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    week_number = Column(Integer, nullable=False)
    completed_sessions = Column(Integer, nullable=False)
    target_sessions = Column(Integer, nullable=False, default=3)
    weight_kg = Column(Float, nullable=False)
    rpe_rating = Column(Integer, nullable=False)
    performance_notes = Column(Text, nullable=True)
    exercise_performance = Column(JSON, nullable=True)
    logged_at = Column(DateTime(timezone=True), server_default=func.now())


class FitnessAgentWorkflow(Base):
    __tablename__ = "fitness_agent_workflows"

    workflow_id = Column(String(100), primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    objective = Column(String(255), nullable=False)
    current_step = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)
    state_data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class FitnessAgentToolCall(Base):
    __tablename__ = "fitness_agent_tool_calls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(String(100), nullable=False, index=True)
    tool_name = Column(String(100), nullable=False)
    inputs = Column(JSON, nullable=False)
    outputs = Column(JSON, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class FitnessAgentApproval(Base):
    __tablename__ = "fitness_agent_approvals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(String(100), nullable=False, index=True)
    approver_id = Column(Integer, nullable=False)
    decision = Column(String(50), nullable=False)
    reason = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
