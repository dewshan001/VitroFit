# DietPlanService/main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from db import Base, engine, get_session
from models import DietPlanInputs, DietPlan
from calculator import calculate_targets
from meal_agent import generate_meals
from auth import get_current_user_id

load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="VitroFit Diet Plan Agent API",
    description="Personalised nutrition plans: deterministic calorie/macro targets + LLM-generated meals.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DietPlanPreferences(BaseModel):
    age: int = Field(..., ge=10, le=100)
    gender: str
    heightCm: float = Field(..., ge=100, le=260)
    weightKg: float = Field(..., ge=30, le=250)
    activityLevel: str
    goal: str
    mealFrequency: str
    restrictions: list[str] = []
    dislikes: str | None = ""
    budgetTier: str
    budgetCustomAmount: float | None = Field(default=None, ge=500, le=15000)
    medicalConditions: list[str] = []
    cookingTime: str


class ConfirmPlanRequest(BaseModel):
    inputs: DietPlanPreferences
    totalCalories: int
    macros: dict
    meals: list
    withinTolerance: bool = True


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "VitroFit Diet Plan Agent"}


@app.post("/api/diet/generate")
async def generate_plan(prefs: DietPlanPreferences, user_id: int = Depends(get_current_user_id)):
    targets = calculate_targets(
        gender=prefs.gender,
        age=prefs.age,
        height_cm=prefs.heightCm,
        weight_kg=prefs.weightKg,
        activity_level=prefs.activityLevel,
        goal=prefs.goal,
    )

    result = await generate_meals(targets, prefs.model_dump())
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])

    return {
        "totalCalories": targets["totalCalories"],
        "macros": targets["macros"],
        "meals": result["meals"],
        "withinTolerance": result["withinTolerance"],
    }


@app.post("/api/diet/confirm")
def confirm_plan(
    req: ConfirmPlanRequest,
    user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_session),
):
    inputs_row = DietPlanInputs(
        user_id=user_id,
        age=req.inputs.age,
        gender=req.inputs.gender,
        height_cm=req.inputs.heightCm,
        weight_kg=req.inputs.weightKg,
        activity_level=req.inputs.activityLevel,
        goal=req.inputs.goal,
        meal_frequency=req.inputs.mealFrequency,
        restrictions=req.inputs.restrictions,
        dislikes=req.inputs.dislikes,
        budget_tier=req.inputs.budgetTier,
        budget_custom_amount=req.inputs.budgetCustomAmount,
        medical_conditions=req.inputs.medicalConditions,
        cooking_time=req.inputs.cookingTime,
    )
    session.add(inputs_row)
    session.flush()  # assigns inputs_row.id without committing yet

    plan_row = DietPlan(
        user_id=user_id,
        inputs_id=inputs_row.id,
        total_calories=req.totalCalories,
        macros=req.macros,
        meals=req.meals,
        within_tolerance=req.withinTolerance,
    )
    session.add(plan_row)
    session.commit()
    session.refresh(plan_row)

    return {"id": plan_row.id, "createdAt": plan_row.created_at.isoformat()}
