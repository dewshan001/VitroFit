"""Offline test setup: no network, no database, no real model."""
import os

os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
os.environ.setdefault("OPENROUTER_MODEL", "test-model")
os.environ.pop("TIME_INJECTION_MODE", None)
os.environ.pop("TIME_INJECTION_BLOCK_SCORE", None)

import uuid
import pytest

from app import llm
from app.schemas import GenerateRequest, TimeSlot, Timetable


class RealServiceCallInTest(AssertionError):
    pass


@pytest.fixture(autouse=True)
def no_real_llm(monkeypatch):
    async def boom(*args, **kwargs):
        raise RealServiceCallInTest("a test tried to call the real model")
    monkeypatch.setattr(llm, "_call_openrouter", boom)


def make_request(**overrides) -> GenerateRequest:
    data = dict(workflowId=uuid.uuid4(), runId=uuid.uuid4(),
                plan={"week": 1, "days": [{"focus": "Push"}]},
                profile={"age": 30, "goal": "muscle_gain"}, preferences="I prefer mornings")
    data.update(overrides)
    return GenerateRequest(**data)


def make_slot(day=1, **overrides) -> TimeSlot:
    data = dict(day=day, startTime="07:00", endTime="08:00", focus="Push", durationMinutes=60,
                description="Bench press, Overhead press, Dips")
    data.update(overrides)
    return TimeSlot(**data)


def make_timetable(slots=3, **slot_overrides) -> Timetable:
    return Timetable(week=1, slots=[make_slot(day=i % 7 + 1, **slot_overrides) for i in range(slots)])


class Recorder:
    def __init__(self):
        self.traces = []

    async def __call__(self, trace):
        self.traces.append(trace)

    @property
    def steps(self):
        return [t.step for t in self.traces]


@pytest.fixture
def recorder():
    return Recorder()
