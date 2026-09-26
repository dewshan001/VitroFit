# DietPlanService/models.py
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from db import Base


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

    created_at = Column(DateTime(timezone=True), server_default=func.now())
