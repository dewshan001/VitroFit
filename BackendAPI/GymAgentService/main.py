# GymAgentService/main.py
import hashlib
import logging
import os
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from db import Base, engine, get_session
from models import GymDetails, GymWorkoutSuggestions
from enrichment_agent import enrich_gym
from vectorstore import store_gym_enrichment
from workout_agent import suggest_workouts

load_dotenv()

logger = logging.getLogger("gym_agent")

CACHE_STALE_DAYS = int(os.getenv("CACHE_STALE_DAYS", "30"))
WORKOUT_CACHE_STALE_DAYS = int(os.getenv("WORKOUT_CACHE_STALE_DAYS", "30"))

Base.metadata.create_all(bind=engine)


def _ensure_contact_columns() -> None:
    """Add the phone/email/opening_hours columns if this table pre-dates them.

    `Base.metadata.create_all` only creates missing tables, not new columns on an
    existing one, so a one-off ALTER TABLE is needed for databases created before
    these columns existed.
    """
    inspector = inspect(engine)
    if "gym_agent_details" not in inspector.get_table_names():
        return

    existing_columns = {col["name"] for col in inspector.get_columns("gym_agent_details")}
    missing = {
        "phone": "VARCHAR(50)",
        "email": "VARCHAR(255)",
        "opening_hours": "VARCHAR(255)",
    }
    with engine.begin() as conn:
        for column, col_type in missing.items():
            if column not in existing_columns:
                conn.execute(text(
                    f"ALTER TABLE gym_agent_details ADD COLUMN IF NOT EXISTS {column} {col_type}"
                ))


_ensure_contact_columns()

app = FastAPI(
    title="VitroFit Gym Agent API",
    description="Nearby-gym equipment/classes enrichment, backed by a free OSM-derived map search on the frontend and an LLM enrichment agent here.",
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


class GymDetailsRequest(BaseModel):
    place_id: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    lat: float | None = None
    lng: float | None = None
    address: str | None = None
    website: str | None = None
    phone: str | None = None
    email: str | None = None
    opening_hours: str | None = None


class WorkoutSuggestionRequest(BaseModel):
    place_id: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    equipment: list[str] = Field(default_factory=list)
    classes: list[str] = Field(default_factory=list)


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

    result = await enrich_gym(
        req.name, req.address, req.website,
        known_phone=req.phone, known_email=req.email, known_hours=req.opening_hours,
    )
    if "error" in result:
        raise HTTPException(status_code=502, detail=f"Enrichment failed: {result['error']}")

    if existing:
        existing.name = req.name
        existing.lat = req.lat
        existing.lng = req.lng
        existing.website = req.website
        existing.phone = result.get("phone")
        existing.email = result.get("email")
        existing.opening_hours = result.get("opening_hours")
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
            phone=result.get("phone"),
            email=result.get("email"),
            opening_hours=result.get("opening_hours"),
            source=result["source"],
            equipment=result["equipment"],
            classes=result["classes"],
        )
        session.add(row)

    session.commit()
    session.refresh(row)

    # Store in vector store for RAG (non-blocking, best-effort)
    try:
        store_gym_enrichment(
            place_id=req.place_id,
            name=req.name,
            address=req.address,
            equipment=result["equipment"],
            classes=result["classes"],
        )
    except Exception:
        logger.exception("Failed to store gym enrichment in vector store for place_id=%s", req.place_id)

    return _to_response(row)


def _workout_fingerprint(equipment: list[str], classes: list[str]) -> str:
    key = "|".join(sorted(equipment)) + "::" + "|".join(sorted(classes))
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


@app.post("/api/gyms/workouts")
async def get_gym_workouts(req: WorkoutSuggestionRequest, session: Session = Depends(get_session)):
    fingerprint = _workout_fingerprint(req.equipment, req.classes)
    existing = session.get(GymWorkoutSuggestions, req.place_id)

    if existing and existing.equipment_fingerprint == fingerprint and existing.workouts:
        age = datetime.now(timezone.utc) - existing.updated_at
        if age < timedelta(days=WORKOUT_CACHE_STALE_DAYS):
            return {"workouts": existing.workouts, "notes": existing.notes or ""}

    result = await suggest_workouts(req.name, req.equipment, req.classes)
    if "error" in result:
        raise HTTPException(status_code=502, detail=f"Workout suggestion failed: {result['error']}")

    # Only cache a real (non-empty) result, so a degenerate generation never poisons
    # future requests for this gym.
    if result["workouts"]:
        if existing:
            existing.equipment_fingerprint = fingerprint
            existing.workouts = result["workouts"]
            existing.notes = result.get("notes", "")
        else:
            session.add(GymWorkoutSuggestions(
                place_id=req.place_id,
                equipment_fingerprint=fingerprint,
                workouts=result["workouts"],
                notes=result.get("notes", ""),
            ))

        session.commit()

    return result


def _to_response(row: GymDetails) -> dict:
    return {
        "place_id": row.place_id,
        "name": row.name,
        "source": row.source,
        "equipment": row.equipment or [],
        "classes": row.classes or [],
        "phone": row.phone,
        "email": row.email,
        "opening_hours": row.opening_hours,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
