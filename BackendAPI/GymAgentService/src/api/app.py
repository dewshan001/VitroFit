# GymAgentService/main.py
import logging
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, FastAPI, Depends, HTTPException
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import inspect, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from contextlib import AsyncExitStack, asynccontextmanager

from src.agent.checkpointer import open_checkpointer
from src.utils.db import Base, engine, get_session
from src.utils.injection_guard import normalise_field
from src.utils.db_migrations import ensure_gym_details_provenance, ensure_tool_call_guard_flags
from src.agent.graph import build_graph
from src.models.llm_client import get_llm
from src.models.db_models import GymDetails, GymWorkoutSuggestions
from src.agent.legacy.enrichment_agent import enrich_gym  # DEPRECATED: legacy endpoint only
from src.agent.runner import WorkflowRunner
from src.agent.store import WorkflowStore, workout_fingerprint
from src.models.vectorstore import store_gym_enrichment
from src.api.routes import MIN_KEY_LENGTH, require_key, router as workflow_router
from src.agent.legacy.workout_agent import suggest_workouts  # DEPRECATED: legacy endpoint only

load_dotenv()

logger = logging.getLogger("gym_agent")

CACHE_STALE_DAYS = int(os.getenv("CACHE_STALE_DAYS", "30"))
AI_SOURCES = frozenset({"ai-scraped", "ai-inferred", "ai-generic"})
# This service is internal: only requests addressed to a local name are accepted (blocks DNS-rebinding
# style access from a browser). Override with GYM_ALLOWED_HOSTS only if a proxy needs another name.
ALLOWED_HOSTS = [h.strip() for h in os.getenv("GYM_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if h.strip()]
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
ensure_gym_details_provenance(engine)
ensure_tool_call_guard_flags(engine)

def _index_published(request: dict, facts: dict, recs: dict) -> None:
    """Best-effort RAG indexing of approved gym data (never blocks publication)."""
    store_gym_enrichment(
        place_id=request["place_id"],
        name=request["name"],
        address=request.get("address"),
        equipment=facts["equipment"],
        classes=facts["classes"],
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build the 4-agent workflow engine. If Postgres/checkpointer is down, only the
    /internal/workflows routes are unavailable (503); legacy routes keep working."""
    stack = AsyncExitStack()
    app.state.runner = None
    if len(os.getenv("GYM_AGENT_KEY", "")) < MIN_KEY_LENGTH:
        logger.error(
            "GYM_AGENT_KEY is missing or shorter than %d characters: every request will be refused "
            "with 503 until it is set (and the same value configured in the ASP.NET API).", MIN_KEY_LENGTH
        )
    try:
        checkpointer = await stack.enter_async_context(open_checkpointer())
        store = WorkflowStore()
        graph = build_graph(store, get_llm, checkpointer, on_published=_index_published)
        runner = WorkflowRunner(store, graph)
        recovered = await runner.recover()
        if recovered:
            logger.warning("Marked %d interrupted workflow(s) as Failed", recovered)
        app.state.runner = runner
    except Exception:
        logger.exception("Workflow engine failed to start; /internal/workflows is disabled")
    try:
        yield
    finally:
        await stack.aclose()


app = FastAPI(
    title="VitroFit Gym Agent (internal)",
    description=(
        "INTERNAL service. Only the ASP.NET Core API calls it, with the shared X-Gym-Agent-Key header; "
        "React and Flutter never do. Bound to 127.0.0.1, no CORS, no public docs."
    ),
    version="3.0.0",
    lifespan=lifespan,
    # Nothing here is for browsers or humans: no interactive docs or schema on a service that is internal.
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.include_router(workflow_router)
# No CORS middleware on purpose: a browser must never be able to call this service directly.
app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)

# Gym details / workout suggestions for ASP.NET (/api/gyms/*), behind the same service key.
gyms_router = APIRouter(prefix="/internal/gyms", dependencies=[Depends(require_key)])


class GymDetailsRequest(BaseModel):
    place_id: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    lat: float | None = None
    lng: float | None = None
    address: str | None = Field(default=None, max_length=500)
    website: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    opening_hours: str | None = Field(default=None, max_length=255)

    @field_validator("place_id", "name", "address", "website", "phone", "email", "opening_hours", mode="before")
    @classmethod
    def _normalise(cls, value):
        return normalise_field(value) if isinstance(value, str) else value


class WorkoutSuggestionRequest(BaseModel):
    place_id: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    equipment: list[str] = Field(default_factory=list, max_length=60)
    classes: list[str] = Field(default_factory=list, max_length=60)

    @field_validator("place_id", "name", mode="before")
    @classmethod
    def _normalise(cls, value):
        return normalise_field(value) if isinstance(value, str) else value

    @field_validator("equipment", "classes", mode="before")
    @classmethod
    def _normalise_items(cls, values):
        return [normalise_field(v) if isinstance(v, str) else v for v in values] if isinstance(values, list) else values


def _aware(value: datetime) -> datetime:
    """Timestamps are stored in UTC; some databases (SQLite) return them without tzinfo."""
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "VitroFit Gym Agent"}


@gyms_router.post("/details")
async def get_gym_details(req: GymDetailsRequest, session: Session = Depends(get_session)):
    existing = session.get(GymDetails, req.place_id)

    if existing and existing.source == "verified":
        return _to_response(existing)

    if existing:
        age = datetime.now(timezone.utc) - _aware(existing.updated_at)
        if age < timedelta(days=CACHE_STALE_DAYS):
            return _to_response(existing)

    result = await enrich_gym(
        req.name, req.address, req.website,
        known_phone=req.phone, known_email=req.email, known_hours=req.opening_hours,
    )
    if "error" in result:
        raise HTTPException(status_code=502, detail=f"Enrichment failed: {result['error']}")

    # The legacy path can only ever produce AI sources; 'verified' exists only via an approved workflow.
    source = result["source"] if result.get("source") in AI_SOURCES else "ai-generic"

    if existing:
        # One conditional UPDATE instead of check-then-write: if an approval promoted this gym
        # to 'verified' after we read it, zero rows change and the verified data is returned.
        updated = session.execute(
            update(GymDetails)
            .where(GymDetails.place_id == req.place_id, GymDetails.source != "verified")
            .values(
                name=req.name,
                lat=req.lat,
                lng=req.lng,
                website=req.website,
                phone=result.get("phone"),
                email=result.get("email"),
                opening_hours=result.get("opening_hours"),
                source=source,
                equipment=result["equipment"],
                classes=result["classes"],
            )
        ).rowcount
        session.commit()
        session.refresh(existing)
        if updated == 0:
            return _to_response(existing)
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
            source=source,
            equipment=result["equipment"],
            classes=result["classes"],
        )
        session.add(row)
        try:
            session.commit()
        except IntegrityError:
            # Someone (an approval, or a concurrent request) created this gym first: keep theirs.
            session.rollback()
            current = session.get(GymDetails, req.place_id)
            if current is None:
                raise
            return _to_response(current)
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


@gyms_router.post("/workouts")
async def get_gym_workouts(req: WorkoutSuggestionRequest, session: Session = Depends(get_session)):
    fingerprint = workout_fingerprint(req.equipment, req.classes)
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


app.include_router(gyms_router)
