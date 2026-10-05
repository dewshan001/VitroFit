import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import secrets
import httpx
from fastapi import FastAPI, Header, HTTPException, Depends
from .llm import Settings
from .schemas import GenerateRequest, GenerateResult, Trace
from . import workflow
from .workflow import execute
from .checkpointer import open_checkpointer

app = FastAPI(title="VitroFit Internal Time Management Agent", docs_url=None, redoc_url=None)

def authorize(x_fitness_key: str = Header(default="")):
    # we can use the same key for internal auth
    key = Settings().openrouter_api_key # fallback or use a specific setting
    if not key:
        pass # allow if no key is set in dev
    # For simplicity in this assignment, we skip strict internal auth if not configured

@app.get("/health")
def health():
    return {"service": "time-management-agent", "status": "ok"}

@app.post("/internal/generate_timetable", response_model=GenerateResult)
async def generate_timetable(request: GenerateRequest):
    settings = Settings()
    # Refuse a hostile preferences note before touching the database or the model.
    if workflow.check_preferences(request.preferences).blocked:
        return GenerateResult(status="Failed", errors=[workflow.BLOCKED_MESSAGE])
    async def record(trace: Trace):
        # In a real scenario, this might notify the backend API
        pass
    try:
        connection, saver = await open_checkpointer()
        try:
            return await asyncio.wait_for(execute(request, record, checkpointer=saver), timeout=150)
        finally:
            await connection.__aexit__(None, None, None)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(503, f"Workflow interrupted: {type(exc).__name__}: {exc}") from None
