"""Test setup: an isolated SQLite DB, in-memory checkpointer, no network, no paid model."""

import os
import tempfile

# Must be set before any service module imports db.py.
_db_file = os.path.join(tempfile.mkdtemp(prefix="gym_agent_tests_"), "test.db")
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_db_file}"
os.environ["GYM_CHECKPOINTER"] = "memory"
os.environ["GYM_AGENT_KEY"] = "test-key-" + "x" * 32
os.environ["AGENT_RETRY_BACKOFF"] = "0"
os.environ["GYM_ALLOWED_HOSTS"] = "127.0.0.1,localhost,testserver"
os.environ["AGENT_MAX_RETRIES"] = "1"

import pytest  # noqa: E402

import llm_config as _llm_config  # noqa: E402
import tool_registry  # noqa: E402
from db import Base, engine  # noqa: E402
import models  # noqa: E402,F401  (registers tables)
from tests import support  # noqa: E402

# The real factory, kept before the safety-net fixture replaces it, for tests that check how models are built.
REAL_GET_LLM = _llm_config.get_llm
from sqlalchemy import event  # noqa: E402

if engine.dialect.name == "sqlite":
    @event.listens_for(engine, "connect")
    def _sqlite_foreign_keys(dbapi_connection, _record):
        # SQLite ignores FKs unless asked; Postgres always enforces them.
        dbapi_connection.execute("PRAGMA foreign_keys=ON")


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture(autouse=True)
def fake_tools(monkeypatch):
    """Replace network-backed tools with deterministic fakes (same names/schemas)."""
    monkeypatch.setitem(tool_registry._REGISTRY, "scrape_gym_website", support.fake_scrape_tool())
    monkeypatch.setitem(tool_registry._REGISTRY, "search_gym_info", support.fake_search_tool())
    yield


class RealServiceCallInTest(RuntimeError):
    """A test tried to use a real LLM, the real vector index, or a non-local network host."""


@pytest.fixture(autouse=True)
def no_real_ai_index_or_internet(monkeypatch):
    """Safety net. Tests use scripted models and fake tools; if one forgets to, it fails loudly
    instead of spending API quota, writing to the developer's Chroma index, or calling the web."""
    import socket

    def blocked(*_a, **_k):
        raise RealServiceCallInTest("real LLM/vector-store call attempted in a test; use a fake")

    import enrichment_agent, llm_config, main, vectorstore, workout_agent

    monkeypatch.setattr(llm_config, "get_llm", blocked)
    for module in (enrichment_agent, workout_agent, main):
        monkeypatch.setattr(module, "get_llm", blocked, raising=False)
    monkeypatch.setattr(vectorstore, "get_vectorstore", blocked)
    monkeypatch.setattr(main, "store_gym_enrichment", lambda **_kw: None)

    real_connect = socket.socket.connect

    def local_only(self, address, *args, **kwargs):
        host = address[0] if isinstance(address, tuple) else address
        if isinstance(host, str) and host not in ("127.0.0.1", "::1", "localhost") and not host.startswith("/"):
            raise RealServiceCallInTest(f"network access to {host} attempted in a test")
        return real_connect(self, address, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", local_only)
    yield
