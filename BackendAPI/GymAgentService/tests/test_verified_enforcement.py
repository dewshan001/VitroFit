"""'verified' can only come from an approved workflow, and the database itself enforces it."""

import asyncio
import os
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from langgraph.types import Command
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

import src.api.app as main
from src.models.contracts import ApprovalDecision
from src.utils.db import SessionLocal
from src.models.db_models import GymDetails, GymWorkflow, GymWorkoutSuggestions
from src.agent.store import PublishRefused, WorkflowStore
from tests.support import FakeModel, golden_facts, golden_recs, gym_request, seed_verified_gym
from tests.test_workflow import decide, make_runner, run, start


KEY_HEADER = {"X-Gym-Agent-Key": os.environ["GYM_AGENT_KEY"]}


def details(place="place-1"):
    with SessionLocal() as s:
        return s.get(GymDetails, place)


def details_count():
    with SessionLocal() as s:
        return len(s.scalars(select(GymDetails)).all())


# ── the database constraint ─────────────────────────────────────────────


def test_database_refuses_verified_without_a_workflow():
    with SessionLocal() as s:
        s.add(GymDetails(place_id="p", name="n", source="verified", equipment=[], classes=[]))
        with pytest.raises(IntegrityError):
            s.commit()


def test_database_refuses_verified_workflow_id_that_does_not_exist():
    with SessionLocal() as s:
        s.add(GymDetails(place_id="p", name="n", source="verified", equipment=[], classes=[], verified_workflow_id="ghost"))
        with pytest.raises(IntegrityError):
            s.commit()


def test_an_existing_ai_row_cannot_be_flipped_to_verified_by_a_plain_update():
    with SessionLocal() as s:
        s.add(GymDetails(place_id="p", name="n", source="ai-scraped", equipment=["x"], classes=[]))
        s.commit()
    with SessionLocal() as s:
        s.get(GymDetails, "p").source = "verified"
        with pytest.raises(IntegrityError):
            s.commit()


def test_ai_rows_need_no_workflow():
    with SessionLocal() as s:
        for i, src in enumerate(("ai-scraped", "ai-inferred", "ai-generic")):
            s.add(GymDetails(place_id=f"p{i}", name="n", source=src, equipment=[], classes=[]))
        s.commit()
    assert details_count() == 3


def test_a_workflow_that_vouches_for_verified_data_cannot_be_deleted():
    wid = seed_verified_gym()
    with SessionLocal() as s:
        s.delete(s.get(GymWorkflow, wid))
        with pytest.raises(IntegrityError):
            s.commit()
    assert details().source == "verified"


# ── store.publish does not trust its caller ─────────────────────────────


def ready_workflow(**overrides):
    """A workflow row that has passed validation and been approved, as the graph leaves it."""
    store = WorkflowStore()
    req = gym_request().model_dump(mode="json")
    wid = store.create(req, "user-1")
    delta = dict(
        facts=golden_facts().model_dump(mode="json"),
        recommendations=golden_recs().model_dump(mode="json"),
        status="Running",
        approval_status="approved",
        approved_by="owner-9",
        approver_role="Admin",
        decided_at=datetime.now(timezone.utc).isoformat(),
    )
    delta.update(overrides)
    store.apply(wid, delta)
    return store, wid


def test_publish_promotes_and_records_provenance_from_the_row():
    store, wid = ready_workflow()
    store.publish(wid)
    d = details()
    assert d.source == "verified" and d.verified_workflow_id == wid
    assert d.verified_by == "owner-9" and d.verified_at is not None
    assert d.phone == "+94 11 234 5678" and "treadmill" in d.equipment
    assert store.get(wid)["status"] == "Published"
    with SessionLocal() as s:
        assert len(s.get(GymWorkoutSuggestions, "place-1").workouts) == 4


@pytest.mark.parametrize(
    "overrides,reason",
    [
        ({"approval_status": "none"}, "approval is 'none'"),
        ({"approval_status": "pending"}, "approval is 'pending'"),
        ({"approval_status": "rejected"}, "approval is 'rejected'"),
        ({"approval_status": "revision_requested"}, "approval is 'revision_requested'"),
        ({"approver_role": "User"}, "approver role"),
        ({"approver_role": "Trainer"}, "approver role"),
        ({"approver_role": None}, "approver role"),
        ({"approved_by": None}, "approver role"),
        ({"facts": None}, "no facts"),
        ({"recommendations": None}, "no facts"),
    ],
)
def test_publish_refuses_anything_the_row_does_not_record_as_approved(overrides, reason):
    store, wid = ready_workflow(**overrides)
    with pytest.raises(PublishRefused, match=reason):
        store.publish(wid)
    assert details_count() == 0 and store.get(wid)["status"] != "Published"
    with SessionLocal() as s:
        assert s.get(GymWorkoutSuggestions, "place-1") is None


def test_publish_refuses_unknown_and_already_published_workflows():
    store, wid = ready_workflow()
    with pytest.raises(PublishRefused, match="does not exist"):
        store.publish("nope")
    store.publish(wid)
    with pytest.raises(PublishRefused, match="already published"):
        store.publish(wid)


def test_a_refused_publish_leaves_existing_verified_data_intact():
    seed_verified_gym()
    store, wid = ready_workflow(approver_role="User")
    with pytest.raises(PublishRefused):
        store.publish(wid)
    assert details().equipment == ["old"] and details().verified_workflow_id == "seed-place-1"


def test_publish_takes_the_data_from_the_row_not_from_the_caller():
    store, wid = ready_workflow()
    # There is no way to hand publish() different facts: it only accepts the workflow id.
    import inspect

    assert list(inspect.signature(store.publish).parameters) == ["workflow_id"]


# ── through the graph ───────────────────────────────────────────────────


def test_a_full_approved_run_links_the_verified_row_to_its_workflow_and_approver():
    async def scenario():
        runner = make_runner(FakeModel())
        wid = await start(runner)
        await decide(runner, wid, kind="approve", role="Gym_Owner", reason="ok")
        return wid

    wid = run(scenario())
    d = details()
    assert (d.source, d.verified_workflow_id, d.verified_by) == ("verified", wid, "owner-9")
    assert d.verified_at is not None


@pytest.mark.parametrize("kind", ["reject", "revise"])
def test_reject_and_revise_never_create_verified_data(kind):
    async def scenario():
        runner = make_runner(FakeModel())
        wid = await start(runner)
        await decide(runner, wid, kind=kind, reason="no")
        return wid

    run(scenario())
    assert details() is None


def test_an_unauthorised_resume_leaves_the_run_waiting_and_publishes_nothing():
    async def scenario():
        runner = make_runner(FakeModel())
        wid = await start(runner)
        bad = ApprovalDecision(decision="approve", actor_id="x", actor_role="User").model_dump(mode="json")
        await runner.graph.ainvoke(Command(resume=bad), runner._config(wid))
        return wid

    wid = run(scenario())
    assert details() is None and WorkflowStore().get(wid)["status"] == "AwaitingApproval"


# ── the legacy endpoint can never create or overwrite verified data ─────


class Legacy:
    """The legacy endpoint with the AI call replaced by a scripted result."""

    def __init__(self):
        self.client = TestClient(main.app)
        self.calls = []
        self.hook = None  # runs while the "AI" is busy: lets a test act in the middle of a request
        self.result = {
            "source": "ai-scraped", "equipment": ["AI treadmill"], "classes": [],
            "phone": None, "email": None, "opening_hours": None,
        }

    def post(self, body):
        return self.client.post("/internal/gyms/details", json=body, headers=KEY_HEADER).json()


@pytest.fixture
def legacy(monkeypatch):
    state = Legacy()

    async def fake_enrich(name, address, website, **known):
        state.calls.append(name)
        if state.hook:
            state.hook()
        return state.result

    monkeypatch.setattr(main, "enrich_gym", fake_enrich)
    monkeypatch.setattr(main, "store_gym_enrichment", lambda **kw: None)
    return state


BODY = {"place_id": "place-1", "name": "FitZone"}


def make_stale(place="place-1"):
    with SessionLocal() as s:
        s.execute(update(GymDetails).where(GymDetails.place_id == place).values(updated_at=datetime.now(timezone.utc) - timedelta(days=90)))
        s.commit()


def test_legacy_endpoint_returns_verified_data_without_calling_the_ai(legacy):
    seed_verified_gym()
    body = legacy.post(BODY)
    assert body["source"] == "verified" and body["equipment"] == ["old"]
    assert legacy.calls == []


def test_legacy_endpoint_cannot_write_verified_even_if_the_agent_claims_it(legacy):
    legacy.result = {**legacy.result, "source": "verified"}
    body = legacy.post(BODY)
    assert body["source"] == "ai-generic" and details().source == "ai-generic"
    assert details().verified_workflow_id is None


def test_legacy_update_of_an_ai_row_still_works(legacy):
    with SessionLocal() as s:
        s.add(GymDetails(place_id="place-1", name="old", source="ai-generic", equipment=[], classes=[]))
        s.commit()
    make_stale()
    body = legacy.post(BODY)
    assert body["source"] == "ai-scraped" and body["equipment"] == ["AI treadmill"]


def test_race_verified_between_the_read_and_the_write_is_not_overwritten(legacy):
    """An approval lands while the (slow) enrichment is running."""
    with SessionLocal() as s:
        s.add(GymDetails(place_id="place-1", name="old", source="ai-generic", equipment=[], classes=[]))
        s.commit()
    make_stale()

    def approve_meanwhile():
        store, wid = ready_workflow()
        store.publish(wid)

    legacy.hook = approve_meanwhile
    body = legacy.post(BODY)

    assert body["source"] == "verified" and "treadmill" in body["equipment"]
    assert "AI treadmill" not in details().equipment
    assert details().verified_workflow_id is not None


def test_race_gym_created_as_verified_before_the_legacy_insert_is_kept(legacy):
    legacy.hook = lambda: seed_verified_gym()
    body = legacy.post(BODY)
    assert body["source"] == "verified" and body["equipment"] == ["old"]
    assert details_count() == 1
