import os
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver

from src.agent.graph import build_graph
from src.agent.runner import WorkflowRunner
from src.agent.store import WorkflowStore
from tests.support import FakeModel
from src.api.routes import router

KEY = os.environ["GYM_AGENT_KEY"]
AUTH = {"X-Gym-Agent-Key": KEY}
BODY = {"place_id": "place-1", "name": "FitZone", "address": "Colombo", "website": "https://fitzone.lk", "requested_by": "user-1"}


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    store = WorkflowStore()
    app.state.runner = WorkflowRunner(store, build_graph(store, FakeModel(), MemorySaver(), None), budget_seconds=30)
    with TestClient(app) as c:
        yield c


def wait_for(client, wid, status):
    for _ in range(100):
        body = client.get(f"/internal/workflows/{wid}", headers=AUTH).json()
        if body["status"] == status:
            return body
        time.sleep(0.05)
    pytest.fail(f"workflow never reached {status}; last={body['status']}")


def test_missing_or_wrong_service_key_is_401(client):
    assert client.get("/internal/workflows").status_code == 401
    assert client.get("/internal/workflows", headers={"X-Gym-Agent-Key": "nope"}).status_code == 401
    assert client.post("/internal/workflows", json=BODY).status_code == 401


def test_unconfigured_or_short_key_fails_closed(client, monkeypatch):
    monkeypatch.setenv("GYM_AGENT_KEY", "short")
    assert client.get("/internal/workflows", headers={"X-Gym-Agent-Key": "short"}).status_code == 503


def test_engine_down_is_503():
    app = FastAPI()
    app.include_router(router)
    app.state.runner = None
    with TestClient(app) as c:
        assert c.get("/internal/workflows", headers=AUTH).status_code == 503


def test_invalid_body_is_422_and_unknown_fields_are_rejected(client):
    assert client.post("/internal/workflows", json={**BODY, "name": ""}, headers=AUTH).status_code == 422
    assert client.post("/internal/workflows", json={**BODY, "role": "Admin"}, headers=AUTH).status_code == 422


def test_unknown_workflow_is_404(client):
    assert client.get("/internal/workflows/nope", headers=AUTH).status_code == 404
    assert client.get("/internal/workflows/nope/events", headers=AUTH).status_code == 404


def test_full_http_flow_start_review_role_check_approve(client):
    started = client.post("/internal/workflows", json=BODY, headers=AUTH)
    assert started.status_code == 202
    wid = started.json()["id"]

    paused = wait_for(client, wid, "AwaitingApproval")
    assert paused["approvalStatus"] == "pending"

    events = client.get(f"/internal/workflows/{wid}/events", headers=AUTH).json()
    assert {"planner", "gym_analysis", "workout_recommendation", "validator"} <= {e["agent"] for e in events}

    pending = client.get("/internal/workflows?status=AwaitingApproval", headers=AUTH).json()
    assert [w["id"] for w in pending] == [wid]

    # a second run for the same gym while one is active is refused
    assert client.post("/internal/workflows", json=BODY, headers=AUTH).status_code == 409

    denied = client.post(
        f"/internal/workflows/{wid}/decision",
        json={"decision": "approve", "actor_id": "u1", "actor_role": "User"},
        headers=AUTH,
    )
    assert denied.status_code == 403
    assert client.get(f"/internal/workflows/{wid}", headers=AUTH).json()["status"] == "AwaitingApproval"

    ok = client.post(
        f"/internal/workflows/{wid}/decision",
        json={"decision": "approve", "reason": "ok", "actor_id": "owner-1", "actor_role": "Gym_Owner"},
        headers=AUTH,
    )
    assert ok.status_code == 202
    done = wait_for(client, wid, "Published")
    assert done["approvedBy"] == "owner-1"

    again = client.post(
        f"/internal/workflows/{wid}/decision",
        json={"decision": "approve", "actor_id": "owner-1", "actor_role": "Admin"},
        headers=AUTH,
    )
    assert again.status_code == 409
