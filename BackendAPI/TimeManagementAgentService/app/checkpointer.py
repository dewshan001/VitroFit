"""Share durable LangGraph checkpoints in the existing PostgreSQL database."""
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# One shared env file for the whole backend (BackendAPI/.env), independent of the working directory.
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class CheckpointSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")
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
