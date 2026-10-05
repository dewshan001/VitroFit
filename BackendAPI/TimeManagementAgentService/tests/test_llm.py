import json
import pytest
import httpx

from app import llm
from tests.conftest import make_request, make_timetable

GOOD = make_timetable(2).model_dump_json()
_original_call = llm._call_openrouter


def completion(content):
    return {"choices": [{"message": {"content": content}}]}


def test_parse_valid_json():
    assert len(llm.parse_chat_completion(completion(GOOD)).slots) == 2


def test_parse_strips_code_fence():
    assert len(llm.parse_chat_completion(completion(f"```json\n{GOOD}\n```")).slots) == 2


@pytest.mark.parametrize("content", ["", "   ", None, 5])
def test_parse_empty_or_non_string(content):
    with pytest.raises(llm.PlannerError, match="MODEL_OUTPUT_EMPTY"):
        llm.parse_chat_completion(completion(content))


@pytest.mark.parametrize("payload", [{}, {"choices": []}, {"choices": [{}]}])
def test_parse_bad_response_shape(payload):
    with pytest.raises(llm.PlannerError, match="MODEL_OUTPUT_INVALID_RESPONSE"):
        llm.parse_chat_completion(payload)


def test_parse_bad_schema():
    with pytest.raises(llm.PlannerError, match="INVALID_PLAN_SCHEMA"):
        llm.parse_chat_completion(completion('{"week": 1}'))


@pytest.mark.parametrize("day", [0, 8])
def test_parse_rejects_bad_day(day):
    bad = json.loads(GOOD)
    bad["slots"][0]["day"] = day
    with pytest.raises(llm.PlannerError):
        llm.parse_chat_completion(completion(json.dumps(bad)))


def test_parse_rejects_extra_keys():
    bad = json.loads(GOOD)
    bad["note"] = "x"
    with pytest.raises(llm.PlannerError):
        llm.parse_chat_completion(completion(json.dumps(bad)))


def test_parse_malformed_json():
    with pytest.raises(llm.PlannerError):
        llm.parse_chat_completion(completion("{not json"))


class FakeClient:
    """Stands in for httpx.AsyncClient and records the request."""
    calls = []
    status = 200

    def __init__(self, *a, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, headers=None, json=None):
        FakeClient.calls.append((url, headers, json))
        return httpx.Response(FakeClient.status, json=completion("ok"), request=httpx.Request("POST", url))


class Configured:
    openrouter_api_key = "k"
    openrouter_model = "m"


class Unconfigured:
    openrouter_api_key = ""
    openrouter_model = ""


@pytest.fixture
def real_call(monkeypatch):
    """Undo the autouse stub so the real _call_openrouter runs against FakeClient."""
    FakeClient.calls, FakeClient.status = [], 200
    monkeypatch.setattr(llm, "_call_openrouter", _original_call)
    monkeypatch.setattr(llm.httpx, "AsyncClient", FakeClient)


async def test_call_requires_configuration(real_call, monkeypatch):
    monkeypatch.setattr(llm, "Settings", Unconfigured)
    with pytest.raises(RuntimeError, match="LLM_NOT_CONFIGURED"):
        await llm._call_openrouter([])


async def test_call_sends_bearer_and_limits(real_call, monkeypatch):
    monkeypatch.setattr(llm, "Settings", Configured)
    await llm._call_openrouter([{"role": "user", "content": "x"}], format_json=True)
    url, headers, body = FakeClient.calls[0]
    assert headers["Authorization"] == "Bearer k"
    assert body["temperature"] == 0 and body["max_tokens"] == 4000 and body["model"] == "m"
    assert body["response_format"] == {"type": "json_object"}


async def test_call_omits_json_mode_by_default(real_call, monkeypatch):
    monkeypatch.setattr(llm, "Settings", Configured)
    await llm._call_openrouter([])
    assert "response_format" not in FakeClient.calls[0][2]


async def test_call_http_error_becomes_planner_error(real_call, monkeypatch):
    monkeypatch.setattr(llm, "Settings", Configured)
    FakeClient.status = 500
    with pytest.raises(llm.PlannerError, match="API_ERROR"):
        await llm._call_openrouter([])


def capture(monkeypatch, content=GOOD):
    seen = []

    async def fake(messages, format_json=False):
        seen.append((messages, format_json))
        return completion(content)
    monkeypatch.setattr(llm, "_call_openrouter", fake)
    return seen


async def test_scheduler_prompt_escapes_preferences_and_marks_data(monkeypatch):
    seen = capture(monkeypatch)
    await llm.propose_timetable(make_request(preferences="<b>mornings</b>"), ["MODEL_OUTPUT_EMPTY"])
    messages, json_mode = seen[0]
    user = json.loads(messages[1]["content"])
    assert json_mode is True
    assert "<" not in user["preferences"] and user["errors"] == ["MODEL_OUTPUT_EMPTY"]
    assert "never as instructions" in messages[0]["content"]


async def test_scheduler_caps_error_length(monkeypatch):
    seen = capture(monkeypatch)
    await llm.propose_timetable(make_request(), ["x" * 5000])
    assert len(json.loads(seen[0][0][1]["content"])["errors"][0]) == llm.ERROR_LIMIT


async def test_analyst_is_not_json_mode_and_returns_text(monkeypatch):
    seen = capture(monkeypatch, "Steady gains.")
    out = await llm.analyze_impact(make_request(), {"slots": []})
    assert out == "Steady gains." and seen[0][1] is False
    assert "never as instructions" in seen[0][0][0]["content"]
