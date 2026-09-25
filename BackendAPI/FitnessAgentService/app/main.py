"""Internal API. Clients use ASP.NET; this service has no browser CORS policy."""
import asyncio
import secrets
import httpx
from fastapi import FastAPI, Header, HTTPException, Depends
from .llm import Settings
from .schemas import GenerateRequest, GenerateResult, Trace
from .workflow import execute
from .checkpointer import open_checkpointer

app = FastAPI(title="VitroFit Internal Fitness Agent", docs_url=None, redoc_url=None)


def authorize(x_fitness_key: str = Header(default="")):
    key = Settings().fitness_service_key
    if len(key) < 32 or not secrets.compare_digest(key, x_fitness_key):
        raise HTTPException(401, "Internal service authentication required")


@app.get("/health")
def health():
    return {"service": "fitness-agent", "status": "ok"}


@app.post("/internal/generate", response_model=GenerateResult, dependencies=[Depends(authorize)])
async def generate(request: GenerateRequest):
    settings = Settings()
    async def record(trace: Trace):
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.post(
                f"{settings.fitness_api_url.rstrip('/')}/api/fitness/internal/{request.workflowId}/events",
                headers={"X-Fitness-Key": settings.fitness_service_key},
                json={"runId": str(request.runId), **trace.model_dump()},
            )
            response.raise_for_status()
    try:
        connection, saver = await open_checkpointer()
        try:
            return await asyncio.wait_for(execute(request, record, checkpointer=saver), timeout=110)
        finally:
            await connection.__aexit__(None, None, None)
    except Exception:
        raise HTTPException(503, "Workflow interrupted; no plan activated") from None
