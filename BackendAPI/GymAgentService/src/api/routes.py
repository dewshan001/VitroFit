"""Internal workflow API. Called only by ASP.NET Core (never by React/Flutter).

Every route requires the shared X-Gym-Agent-Key header. ASP.NET authenticates the end
user and passes the verified actor id/role; this service re-checks the role for the
approval decision (defence in depth).
"""

import asyncio
import os
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request

from src.models.contracts import ApprovalDecision, PlannerInput
from src.agent.runner import Conflict, NotFound, WorkflowRunner
from src.agent.store import WorkflowStore

MIN_KEY_LENGTH = 32


class StartWorkflowBody(PlannerInput):
    requested_by: str


def require_key(x_gym_agent_key: str | None = Header(default=None)) -> None:
    expected = os.getenv("GYM_AGENT_KEY", "")
    if len(expected) < MIN_KEY_LENGTH:
        raise HTTPException(status_code=503, detail="Service key is not configured")
    if not x_gym_agent_key or not secrets.compare_digest(
        x_gym_agent_key.encode("utf-8"), expected.encode("utf-8")
    ):
        raise HTTPException(status_code=401, detail="Invalid service key")


def get_runner(request: Request) -> WorkflowRunner:
    runner = getattr(request.app.state, "runner", None)
    if runner is None:
        raise HTTPException(status_code=503, detail="Workflow engine is unavailable")
    return runner


router = APIRouter(prefix="/internal/workflows", dependencies=[Depends(require_key)])


@router.post("", status_code=202)
async def start_workflow(body: StartWorkflowBody, runner: WorkflowRunner = Depends(get_runner)):
    store: WorkflowStore = runner.store
    if await asyncio.to_thread(store.active_for_place, body.place_id):
        raise HTTPException(status_code=409, detail="A workflow for this gym is already active")
    request = PlannerInput.model_validate(body.model_dump(exclude={"requested_by"}))
    workflow_id = await runner.start(request, body.requested_by)
    return {"id": workflow_id, "status": "Running"}


@router.get("")
async def list_workflows(
    status: str | None = Query(default=None),
    requested_by: str | None = Query(default=None, alias="requestedBy"),
    limit: int = Query(default=50, ge=1, le=100),
    runner: WorkflowRunner = Depends(get_runner),
):
    return await asyncio.to_thread(
        runner.store.list_workflows, status=status, requested_by=requested_by, limit=limit
    )


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str, runner: WorkflowRunner = Depends(get_runner)):
    row = await asyncio.to_thread(runner.store.get, workflow_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return row


@router.get("/{workflow_id}/events")
async def get_events(workflow_id: str, runner: WorkflowRunner = Depends(get_runner)):
    if await asyncio.to_thread(runner.store.get, workflow_id) is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return await asyncio.to_thread(runner.store.events, workflow_id)


@router.post("/{workflow_id}/decision", status_code=202)
async def decide(
    workflow_id: str, decision: ApprovalDecision, runner: WorkflowRunner = Depends(get_runner)
):
    try:
        return await runner.decide(workflow_id, decision)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except NotFound:
        raise HTTPException(status_code=404, detail="Workflow not found")
    except Conflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
