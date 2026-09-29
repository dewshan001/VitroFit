"""Test setup: an isolated SQLite DB, in-memory checkpointer, no network, no paid model."""

import os
import tempfile

# Must be set before any service module imports db.py.
_db_file = os.path.join(tempfile.mkdtemp(prefix="gym_agent_tests_"), "test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_file}"
os.environ["GYM_CHECKPOINTER"] = "memory"
os.environ["GYM_AGENT_KEY"] = "test-key-" + "x" * 32
os.environ["AGENT_RETRY_BACKOFF"] = "0"
os.environ["AGENT_MAX_RETRIES"] = "1"

import pytest  # noqa: E402

import tool_registry  # noqa: E402
from db import Base, engine  # noqa: E402
import models  # noqa: E402,F401  (registers tables)
from tests import support  # noqa: E402


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
