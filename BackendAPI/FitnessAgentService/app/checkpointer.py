"""Share durable LangGraph checkpoints in the existing PostgreSQL database."""
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from pydantic_settings import BaseSettings, SettingsConfigDict


class CheckpointSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    fitness_database_url: str = ""


async def open_checkpointer():
    url = CheckpointSettings().fitness_database_url
    if not url:
        raise RuntimeError("FITNESS_DATABASE_URL is required for durable workflow checkpoints")
    connection = AsyncPostgresSaver.from_conn_string(url)
    saver = await connection.__aenter__()
    # CREATE TABLE IF NOT EXISTS inside the existing database; no separate database.
    await saver.setup()
    return connection, saver
