"""The logging handler is attached, useful, and safe: it never writes prompts, page text or secrets."""

import asyncio
import logging
import re
from pathlib import Path
from uuid import uuid4

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.tools import StructuredTool

import callbacks
import llm_config
from callbacks import GymAgentLoggingHandler, get_handler, safe
from runner import WorkflowRunner
from tests.conftest import REAL_GET_LLM
from tests.support import WEBSITE, FakeModel
from tests.test_workflow import make_runner, run, start
from tools import ScrapeInput


@pytest.fixture(autouse=True)
def fresh_db():
    yield


@pytest.fixture
def log(caplog):
    caplog.set_level(logging.INFO, logger="gym_agent")
    callbacks.logger.addHandler(caplog.handler)
    yield lambda: [r.getMessage() for r in caplog.records if r.name == "gym_agent"]
    callbacks.logger.removeHandler(caplog.handler)


CONTEXT = {"workflow_id": "abcdef1234567890", "langgraph_node": "gym_analysis"}


# ── it is attached ──────────────────────────────────────────────────────


@pytest.mark.parametrize("nvidia", [True, False])
def test_every_model_built_by_get_llm_carries_the_handler(monkeypatch, nvidia):
    monkeypatch.setattr(llm_config, "NVIDIA_API_KEY", "nvapi-test-key" if nvidia else None)
    monkeypatch.setattr(llm_config, "OPENROUTER_API_KEY", "sk-or-test-key")
    model = REAL_GET_LLM(temperature=0.1, max_tokens=50)
    assert any(isinstance(c, GymAgentLoggingHandler) for c in model.callbacks)


def test_one_shared_handler_is_used_everywhere():
    assert get_handler() is get_handler()


def test_the_runner_puts_the_workflow_id_in_the_graph_config():
    config = WorkflowRunner._config("wf-123")
    assert config["metadata"] == {"workflow_id": "wf-123"} and config["configurable"]["thread_id"] == "wf-123"


# ── model calls ─────────────────────────────────────────────────────────


def test_model_calls_are_logged_with_run_id_node_and_timing_but_never_the_prompt_or_reply(log):
    model = FakeListChatModel(responses=["SECRET-REPLY-TEXT"], callbacks=[get_handler()])
    asyncio.run(model.ainvoke("SECRET-PROMPT-TEXT about a gym", config={"metadata": CONTEXT}))

    lines = log()
    start_line = next(l for l in lines if l.startswith("llm start"))
    end_line = next(l for l in lines if l.startswith("llm end"))
    assert "wf=abcdef12" in start_line and "node=gym_analysis" in start_line
    assert re.search(r"ms=\d+", end_line)
    everything = " ".join(lines)
    assert "SECRET-PROMPT-TEXT" not in everything and "SECRET-REPLY-TEXT" not in everything


def test_model_errors_log_the_type_only_never_the_message(log):
    class Boom(BaseChatModel):
        @property
        def _llm_type(self):
            return "boom"

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            raise RuntimeError("provider said: prompt was 'SECRET-PROMPT' key=sk-abcdefghijklmnop123456")

    with pytest.raises(RuntimeError):
        asyncio.run(Boom(callbacks=[get_handler()]).ainvoke("hi", config={"metadata": CONTEXT}))
    line = next(l for l in log() if l.startswith("llm error"))
    assert "type=RuntimeError" in line and "wf=abcdef12" in line
    assert "SECRET-PROMPT" not in line and "sk-abcdefghijklmnop" not in line


# ── tool calls ──────────────────────────────────────────────────────────


def make_tool(output="HOSTILE-PAGE-TEXT " * 5, error=None):
    async def scrape(url: str) -> str:
        if error:
            raise error
        return output

    return StructuredTool.from_function(coroutine=scrape, name="scrape_gym_website", description="d", args_schema=ScrapeInput)


def test_tool_calls_log_the_target_and_the_size_but_never_the_page_content(log):
    asyncio.run(make_tool().ainvoke(
        {"url": "https://fitzone.lk/about?token=SECRET123"},
        config={"callbacks": [get_handler()], "metadata": CONTEXT},
    ))
    lines = log()
    start_line = next(l for l in lines if l.startswith("tool start"))
    end_line = next(l for l in lines if l.startswith("tool end"))
    assert "tool=scrape_gym_website" in start_line and "input=fitzone.lk/about" in start_line
    assert "SECRET123" not in start_line                                  # no query string: it can hold tokens
    assert re.search(r"chars=\d+", end_line) and "wf=abcdef12" in end_line
    assert "HOSTILE-PAGE-TEXT" not in " ".join(lines)


def test_tool_errors_log_the_type_only(log):
    with pytest.raises(ValueError):
        asyncio.run(make_tool(error=ValueError("api_key=sk-abcdefghijklmnop123456 SECRET")).ainvoke(
            {"url": WEBSITE}, config={"callbacks": [get_handler()]}))
    line = next(l for l in log() if l.startswith("tool error"))
    assert "type=ValueError" in line and "SECRET" not in line and "sk-abcdef" not in line


def test_search_queries_are_summarised_briefly(log):
    handler = get_handler()
    handler.on_tool_start({"name": "search_gym_info"}, "x", run_id=uuid4(), inputs={"query": "FitZone Colombo gym " + "x" * 300})
    line = next(l for l in log() if l.startswith("tool start"))
    assert "tool=search_gym_info" in line and len(line) < 200


# ── through a whole workflow ────────────────────────────────────────────


def test_a_workflow_logs_its_tool_calls_with_the_workflow_id(log):
    async def scenario():
        return await start(make_runner(FakeModel()))

    wid = run(scenario())
    starts = [l for l in log() if l.startswith("tool start")]
    assert any("tool=scrape_gym_website" in l and "input=fitzone.lk" in l for l in starts)
    assert any("tool=list_equipment_taxonomy" in l for l in starts)
    assert all(f"wf={wid[:8]}" in l for l in starts)
    assert any(l.startswith("tool end") and "chars=" in l for l in log())


# ── log lines are safe ──────────────────────────────────────────────────


@pytest.mark.parametrize("value,forbidden", [
    ("key sk-abcdefghijklmnop1234", "sk-abcdefghijklmnop1234"),
    ("nvapi-AbCdEfGhIjKlMnOp-1234567", "nvapi-AbCdEfGh"),
    ("tvly-abcdefghijklmnop", "tvly-abcdefgh"),
    ("Authorization: Bearer abc.def-ghi_jkl+mno==", "abc.def-ghi"),
    ("eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcdefghijk", "eyJhbGci"),
    ("api_key=hunter2hunter2", "hunter2"),
    ("password: correcthorse", "correcthorse"),
    ("A" * 60, "A" * 40),
])
def test_secrets_are_redacted(value, forbidden):
    out = safe(value)
    assert forbidden not in out and "[redacted]" in out


def test_newlines_and_control_characters_cannot_forge_log_lines():
    out = safe("real\nERROR [gym_agent] forged line\r\n\x1b[31mred\x00 more")
    assert "\n" not in out and "\r" not in out and "\x1b" not in out and "\x00" not in out and " " not in out


def test_values_are_truncated_and_console_safe():
    out = safe("සුභ දවසක් Gym \U0001f600 " + "word " * 100)
    assert len(out) <= 160
    out.encode("cp1252")                                                   # would raise on a Windows console otherwise
    assert safe(None) == "" and safe(12345) == "12345"


def test_the_handler_source_contains_no_emoji_or_other_non_ascii():
    assert Path(callbacks.__file__).read_text(encoding="utf-8").isascii()


def test_a_logging_problem_never_breaks_a_run():
    handler = get_handler()
    assert handler.raise_error is False
    handler.on_llm_end(object(), run_id=uuid4())                           # malformed response
    handler.on_tool_end(None, run_id=uuid4())
    handler.on_tool_start(None, "x", run_id=uuid4(), inputs="not a dict")
    handler.on_llm_error(Exception("x"), run_id=uuid4())


def test_logger_setup_is_idempotent_and_honours_the_level(monkeypatch):
    before = len(callbacks.logger.handlers)
    callbacks._configure_logger()
    callbacks._configure_logger()
    assert len(callbacks.logger.handlers) == before
    monkeypatch.setenv("GYM_LOG_LEVEL", "WARNING")
    callbacks._configure_logger()
    assert callbacks.logger.level == logging.WARNING
    monkeypatch.setenv("GYM_LOG_LEVEL", "nonsense")
    callbacks._configure_logger()
    assert callbacks.logger.level == logging.INFO
