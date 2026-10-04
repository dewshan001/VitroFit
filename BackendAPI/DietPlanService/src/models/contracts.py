# DietPlanService/src/models/contracts.py
"""Strict Pydantic input/output contract for each of the three diet-plan agents.
workflow.call_tool() validates every agent call against these.
"""
from typing import Literal
from pydantic import BaseModel


class RiskFlag(BaseModel):
    code: str
    message: str


# --- Planner ----------------------------------------------------------------

class PlanResult(BaseModel):
    steps: list[dict]
    route: Literal["standard", "medical_review"]
    allowed_tools: list[str]


# --- Nutrition Analyst Agent ------------------------------------------------

class NutritionAnalystInput(BaseModel):
    prefs: dict


class NutritionAnalystOutput(BaseModel):
    targets: dict
    risk_level: Literal["low", "medium", "high"]
    risk_flags: list[RiskFlag]
    budget_context: dict


# --- Meal Generator Agent ---------------------------------------------------

class MealGeneratorInput(BaseModel):
    targets: dict
    prefs: dict
    corrective_note: str | None = None
    # Set together to request a targeted edit to an existing plan (via the
    # refine_meals tool) instead of a fresh generation (generate_meals).
    current_meals: list[dict] | None = None
    instruction: str | None = None


class MealItem(BaseModel):
    name: str
    portion: str
    calories: float
    macros: dict


class Meal(BaseModel):
    type: str
    label: str
    items: list[MealItem]


class MealGeneratorOutput(BaseModel):
    meals: list[Meal]
    withinTolerance: bool
    error: str | None = None


# --- Safety Validator Agent -------------------------------------------------

class SafetyValidatorInput(BaseModel):
    meals: list[dict]
    targets: dict
    prefs: dict


class SafetyValidatorOutput(BaseModel):
    verdict: Literal["pass", "revise", "reject"]
    violations: list[dict]
