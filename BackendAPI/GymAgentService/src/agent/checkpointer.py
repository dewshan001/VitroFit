"""Durable LangGraph checkpointer (PostgreSQL) so a paused approval survives restarts."""

import os
from contextlib import asynccontextmanager

from src.utils.db import DATABASE_URL


@asynccontextmanager
async def open_checkpointer():
    """Yield a checkpointer. GYM_CHECKPOINTER=memory is for tests/dev only."""
    if os.getenv("GYM_CHECKPOINTER", "postgres") == "memory":
        from langgraph.checkpoint.memory import MemorySaver

        yield MemorySaver()
        return

    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    # psycopg3 wants a plain libpq URL, not the SQLAlchemy driver-qualified one.
    url = DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://")
    async with AsyncPostgresSaver.from_conn_string(url) as saver:
        await saver.setup()
        yield saver
