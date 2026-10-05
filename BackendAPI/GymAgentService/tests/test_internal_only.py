"""The gym service is INTERNAL: only ASP.NET (same machine, shared key) may call it."""

import ipaddress
import os

import pytest
from fastapi.testclient import TestClient
from starlette.middleware.cors import CORSMiddleware

import src.api.app as main
import server

KEY = os.environ["GYM_AGENT_KEY"]
AUTH = {"X-Gym-Agent-Key": KEY}
BROWSER_ORIGIN = {"Origin": "http://localhost:5173"}

DETAILS = {"place_id": "p1", "name": "FitZone"}
WORKOUTS = {"place_id": "p1", "name": "FitZone", "equipment": ["treadmill"], "classes": []}

# Every route the service exposes besides /health, as (method, path, json body).
PROTECTED = [
    ("POST", "/internal/gyms/details", DETAILS),
    ("POST", "/internal/gyms/workouts", WORKOUTS),
    ("POST", "/internal/workflows", {"place_id": "p1", "name": "n", "requested_by": "u"}),
    ("GET", "/internal/workflows", None),
    ("GET", "/internal/workflows/any-id", None),
    ("GET", "/internal/workflows/any-id/events", None),
    ("POST", "/internal/workflows/any-id/decision", {"decision": "approve", "actor_id": "1", "actor_role": "Admin"}),
]


@pytest.fixture
def client():
    return TestClient(main.app)


@pytest.mark.parametrize("method,path,body", PROTECTED)
def test_every_route_refuses_a_call_without_the_service_key(client, method, path, body):
    res = client.request(method, path, json=body)
    assert res.status_code == 401


@pytest.mark.parametrize("method,path,body", PROTECTED)
@pytest.mark.parametrize("key", ["", "wrong", KEY[:-1], KEY + "x", "x" * 100])
def test_every_route_refuses_a_wrong_key(client, method, path, body, key):
    assert client.request(method, path, json=body, headers={"X-Gym-Agent-Key": key}).status_code == 401


@pytest.mark.parametrize("method,path,body", PROTECTED)
def test_every_route_fails_closed_when_the_service_has_no_key(client, monkeypatch, method, path, body):
    monkeypatch.setenv("GYM_AGENT_KEY", "")
    assert client.request(method, path, json=body, headers=AUTH).status_code == 503


@pytest.mark.parametrize("method,path,body", PROTECTED)
def test_a_bearer_token_is_not_a_substitute_for_the_service_key(client, method, path, body):
    assert client.request(method, path, json=body, headers={"Authorization": "Bearer anything"}).status_code == 401


def test_the_old_public_paths_no_longer_exist(client):
    assert client.post("/api/gyms/details", json=DETAILS, headers=AUTH).status_code == 404
    assert client.post("/api/gyms/workouts", json=WORKOUTS, headers=AUTH).status_code == 404


def test_the_correct_key_reaches_the_route(client, monkeypatch):
    async def fake_workouts(name, equipment, classes):
        return {"workouts": [], "notes": "n"}

    monkeypatch.setattr(main, "suggest_workouts", fake_workouts)
    assert client.post("/internal/gyms/workouts", json=WORKOUTS, headers=AUTH).status_code == 200


def test_there_is_no_cors_so_a_browser_cannot_call_the_service(client, monkeypatch):
    async def fake_enrich(name, address, website, **known):
        return {"source": "ai-generic", "equipment": [], "classes": [], "phone": None, "email": None, "opening_hours": None}

    monkeypatch.setattr(main, "enrich_gym", fake_enrich)
    simple = client.post("/internal/gyms/details", json=DETAILS, headers={**AUTH, **BROWSER_ORIGIN})
    assert "access-control-allow-origin" not in simple.headers
    preflight = client.options(
        "/internal/gyms/details",
        headers={**BROWSER_ORIGIN, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "x-gym-agent-key"},
    )
    assert preflight.status_code in (400, 404, 405) and "access-control-allow-origin" not in preflight.headers
    assert not any(m.cls is CORSMiddleware for m in main.app.user_middleware)


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"])
def test_no_public_docs_or_schema(client, path):
    assert client.get(path).status_code == 404


@pytest.mark.parametrize("host", ["evil.example", "gym-agent.example.com", "10.0.0.5", "127.0.0.1.evil.com"])
def test_requests_addressed_to_a_non_local_host_are_refused(host):
    res = TestClient(main.app, base_url=f"http://{host}").get("/health", headers=AUTH)
    assert res.status_code == 400


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "127.0.0.1:8001", "localhost:8001"])
def test_local_hosts_are_accepted(host):
    assert TestClient(main.app, base_url=f"http://{host}").get("/health").status_code == 200


def test_health_reveals_nothing_beyond_liveness(client):
    assert client.get("/health").json() == {"status": "ok", "service": "VitroFit Gym Agent"}


def test_the_server_only_listens_on_loopback():
    assert ipaddress.ip_address(server.HOST).is_loopback


def test_oversized_lists_are_rejected_before_any_work(client):
    body = {**WORKOUTS, "equipment": [f"item {i}" for i in range(61)]}
    assert client.post("/internal/gyms/workouts", json=body, headers=AUTH).status_code == 422
    body = {**DETAILS, "address": "x" * 501}
    assert client.post("/internal/gyms/details", json=body, headers=AUTH).status_code == 422


def test_the_test_suite_cannot_reach_a_real_model_or_the_internet():
    import socket

    import src.models.llm_client as llm_config
    from tests.conftest import RealServiceCallInTest

    with pytest.raises(RealServiceCallInTest):
        llm_config.get_llm()
    with pytest.raises(RealServiceCallInTest):
        socket.create_connection(("example.com", 80), timeout=1)
