# DietPlanService/src/api/app.py
"""The FastAPI application: CORS, table creation and the health check. All
/api/diet endpoints live in routes.py."""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from dotenv import load_dotenv

from src.utils.db import Base, engine
import src.models.db_models  # noqa: F401 - registers every table with Base before create_all
import src.agent.store  # noqa: F401 - registers the audit-trail mirror (events -> diet_workflow_steps)
from src.api.routes import router
from src.utils.db_migrations import ensure_workflow_columns, ensure_workflow_constraints, ensure_plan_columns
from src.agent.runner import recover_interrupted
from src.utils.logger import log_event

load_dotenv()

Base.metadata.create_all(bind=engine)
ensure_workflow_columns(engine)
ensure_plan_columns(engine)
ensure_workflow_constraints(engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """On start-up, finish off runs a crash/restart left in 'running' (nothing is executing them)."""
    try:
        recover_interrupted()
    except Exception:
        log_event("start-up recovery failed")
    yield


app = FastAPI(
    lifespan=lifespan,
    title="VitroFit Diet Plan Agent API",
    description="Personalised nutrition plans: deterministic calorie/macro targets + LLM-generated meals.",
    version="1.0.0",
)

# Optional host allow-list (DIET_ALLOWED_HOSTS="127.0.0.1,localhost"): blocks DNS-rebinding style
# access from a browser. Unset = no restriction, as before.
_allowed_hosts = [h.strip() for h in os.getenv("DIET_ALLOWED_HOSTS", "").split(",") if h.strip()]
if _allowed_hosts:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=_allowed_hosts)

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


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "VitroFit Diet Plan Agent"}


app.include_router(router)
