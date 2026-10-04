# DietPlanService/src/models/schemas.py
"""HTTP request bodies (Pydantic) and the allowed values for each preference field."""
from typing import Literal

from pydantic import BaseModel, Field, field_validator

GenderLiteral = Literal["male", "female", "other"]
ActivityLevelLiteral = Literal["sedentary", "light", "moderate", "active"]
GoalLiteral = Literal["weight loss", "muscle gain", "maintenance", "endurance"]
MealFrequencyLiteral = Literal["3Meals", "4Meals", "5Meals", "intermittent"]
RestrictionLiteral = Literal[
    "vegetarian", "vegan", "halal", "dairy-free", "gluten-free",
    "peanut allergy", "lactose-intolerant",
]
MedicalConditionLiteral = Literal[
    "diabetes", "high blood pressure", "high cholesterol",
    "heart condition", "kidney condition", "thyroid condition",
]
BudgetTierLiteral = Literal["low", "medium", "high", "custom"]
CookingTimeLiteral = Literal["quick", "moderate", "nocook"]


def _sanitize_free_text(v: str | None, max_len: int) -> str | None:
    """Strips control characters and caps length on any free-text field sent
    to the LLM (dislikes, refine instructions) - keeps user text well-formed
    data, never something that could be used to pad/break the JSON prompt.
    """
    if not v:
        return v
    cleaned = "".join(c for c in v if c.isprintable() or c in " \n")
    return cleaned[:max_len]


class DietPlanPreferences(BaseModel):
    age: int = Field(..., ge=10, le=100)
    gender: GenderLiteral
    heightCm: float = Field(..., ge=100, le=260)
    weightKg: float = Field(..., ge=30, le=250)
    activityLevel: ActivityLevelLiteral
    goal: GoalLiteral
    mealFrequency: MealFrequencyLiteral
    restrictions: list[RestrictionLiteral] = []
    dislikes: str | None = ""
    budgetTier: BudgetTierLiteral
    budgetCustomAmount: float | None = Field(default=None, ge=500, le=15000)
    medicalConditions: list[MedicalConditionLiteral] = []
    cookingTime: CookingTimeLiteral

    @field_validator("dislikes")
    @classmethod
    def _sanitize_dislikes(cls, v: str | None) -> str | None:
        return _sanitize_free_text(v, max_len=500)


class ConfirmPlanRequest(BaseModel):
    inputs: DietPlanPreferences
    totalCalories: int
    macros: dict
    meals: list
    withinTolerance: bool = True
    workflowId: str | None = None


class RefinePlanRequest(BaseModel):
    instruction: str = Field(..., min_length=1)

    @field_validator("instruction")
    @classmethod
    def _sanitize_instruction(cls, v: str) -> str:
        cleaned = _sanitize_free_text(v, max_len=300)
        if not cleaned or not cleaned.strip():
            raise ValueError("instruction cannot be empty.")
        return cleaned
