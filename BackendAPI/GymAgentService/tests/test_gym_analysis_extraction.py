import asyncio

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.agent.nodes import gym_analysis
from src.agent.nodes._common import AgentOutputError, parse_json_object
from src.models.contracts import GymFacts

VALID = '{"equipment": ["Treadmill"], "classes": [], "phone": null, "email": null, "opening_hours": null, "evidence": [], "confidence": 0.5}'


def test_parse_ignores_think_blocks_and_fences():
    raw = '<think>maybe {"x": 1} is it</think>\n```json\n' + VALID + "\n```"
    assert parse_json_object(raw)["equipment"] == ["Treadmill"]


@pytest.mark.parametrize("raw", ["", "I could not find anything.", "<think>{}</think>"])
def test_parse_rejects_replies_without_an_answer(raw):
    with pytest.raises(AgentOutputError):
        parse_json_object(raw)


class _PlainLlm:
    """No function calling; replies come from a script."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0

    def with_structured_output(self, schema):
        raise NotImplementedError("model has no function calling")

    async def ainvoke(self, messages):
        self.calls += 1
        return AIMessage(content=self.replies.pop(0) if len(self.replies) > 1 else self.replies[0])


def _extract(llm):
    return asyncio.run(gym_analysis._extract(llm, [HumanMessage(content="Gym: X")]))


def test_empty_first_reply_is_retried_once():
    llm = _PlainLlm(["", VALID])
    facts = _extract(llm)
    assert isinstance(facts, GymFacts) and facts.equipment == ["Treadmill"] and llm.calls == 2


def test_gives_up_after_the_bounded_attempts():
    llm = _PlainLlm([""])
    with pytest.raises(AgentOutputError):
        _extract(llm)
    assert llm.calls == gym_analysis.EXTRACTION_ATTEMPTS


def test_extraction_gets_more_token_room_than_a_tool_turn():
    assert gym_analysis.EXTRACTION_MAX_TOKENS > 900


def test_overlong_evidence_snippet_is_clipped_not_rejected():
    from src.models.contracts import Evidence

    ev = Evidence(field="equipment", source_url=None, snippet="x" * 900)
    assert len(ev.snippet) == 300
