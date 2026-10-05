import uuid
import pytest
from pydantic import ValidationError

from app.schemas import GenerateRequest, GenerateResult, TimeSlot, Timetable, Trace
from tests.conftest import make_request

SLOT = dict(day=1, startTime="07:00", endTime="08:00", focus="Push", durationMinutes=60)


@pytest.mark.parametrize("day", [0, 8, -1])
def test_day_out_of_range_is_rejected(day):
    with pytest.raises(ValidationError):
        TimeSlot(**{**SLOT, "day": day})


@pytest.mark.parametrize("day", [1, 4, 7])
def test_day_in_range_is_accepted(day):
    assert TimeSlot(**{**SLOT, "day": day}).day == day


def test_slot_description_defaults_to_empty():
    assert TimeSlot(**SLOT).description == ""


def test_slot_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        TimeSlot(**SLOT, extra="x")


def test_timetable_requires_slots_list():
    with pytest.raises(ValidationError):
        Timetable(week=1)


def test_request_requires_uuids():
    with pytest.raises(ValidationError):
        GenerateRequest(workflowId="nope", runId=uuid.uuid4(), plan={}, profile={})


def test_request_preferences_default_empty():
    r = GenerateRequest(workflowId=uuid.uuid4(), runId=uuid.uuid4(), plan={}, profile={})
    assert r.preferences == ""


def test_request_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        make_request(unexpected=True)


def test_result_status_is_limited():
    with pytest.raises(ValidationError):
        GenerateResult(status="Done")
    assert GenerateResult(status="Failed").errors == []


def test_trace_defaults():
    t = Trace(step="x", summary="y")
    assert t.durationMs == 0 and t.snapshot == {}
