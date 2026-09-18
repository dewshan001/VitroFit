# GymAgentService/main.py
import os
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from db import Base, engine, get_session
from models import GymDetails
from enrichment_agent import enrich_gym
import fitness_agent.models_fitness  # registers all fitness tables
from fitness_agent.api.fitness_routes import router as fitness_router

load_dotenv()

CACHE_STALE_DAYS = int(os.getenv("CACHE_STALE_DAYS", "30"))

try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Database table check warning: {e}")

app = FastAPI(
    title="VitroFit Gym Agent & Fitness AI API",
    description="Nearby-gym equipment/classes enrichment and AI-powered adaptive fitness planning agent.",
    version="1.0.0",
)

app.include_router(fitness_router)

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


class GymDetailsRequest(BaseModel):
    place_id: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    lat: float | None = None
    lng: float | None = None
    address: str | None = None
    website: str | None = None


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "VitroFit Gym Agent"}


@app.post("/api/gyms/details")
async def get_gym_details(req: GymDetailsRequest, session: Session = Depends(get_session)):
    existing = session.get(GymDetails, req.place_id)

    if existing and existing.source == "verified":
        return _to_response(existing)

    if existing:
        age = datetime.now(timezone.utc) - existing.updated_at
        if age < timedelta(days=CACHE_STALE_DAYS):
            return _to_response(existing)

    result = await enrich_gym(req.name, req.address, req.website)
    if "error" in result:
        raise HTTPException(status_code=502, detail=f"Enrichment failed: {result['error']}")

    if existing:
        existing.name = req.name
        existing.lat = req.lat
        existing.lng = req.lng
        existing.website = req.website
        existing.source = result["source"]
        existing.equipment = result["equipment"]
        existing.classes = result["classes"]
        row = existing
    else:
        row = GymDetails(
            place_id=req.place_id,
            name=req.name,
            lat=req.lat,
            lng=req.lng,
            website=req.website,
            source=result["source"],
            equipment=result["equipment"],
            classes=result["classes"],
        )
        session.add(row)

    session.commit()
    session.refresh(row)
    return _to_response(row)


def _to_response(row: GymDetails) -> dict:
    return {
        "place_id": row.place_id,
        "name": row.name,
        "source": row.source,
        "equipment": row.equipment or [],
        "classes": row.classes or [],
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
