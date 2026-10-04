# DietPlanService/src/agent/runner.py
"""Limits how many plan generations/edits hit the shared LLM endpoint at once and
recovers runs a restart left behind.

Several runs sharing one hosted model slow each other down (and a single user can
start many), so only a few run at once; the rest wait here while their workflow
row stays `running`, which is exactly what the polling UI already shows. The
workflow's own time budget starts only after a slot is acquired, so waiting does
not eat into it.
"""
import asyncio
import os
import weakref

from src.agent.store import fail_stale
from src.utils.db import SessionLocal

MAX_CONCURRENT_WORKFLOWS = max(1, int(os.getenv("DIET_MAX_CONCURRENT_WORKFLOWS", "3")))
# At start-up nothing in this process is running yet, so every 'running' row is orphaned.
# (Raise this only if several instances share one database.)
RECOVER_MAX_AGE_SECONDS = int(os.getenv("DIET_RECOVER_MAX_AGE_SECONDS", "0"))

# One semaphore per event loop: a semaphore must not be shared across loops.
_slots: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Semaphore]" = weakref.WeakKeyDictionary()


def slot() -> asyncio.Semaphore:
    """`async with slot():` around the LLM-bound part of a run."""
    loop = asyncio.get_running_loop()
    semaphore = _slots.get(loop)
    if semaphore is None:
        semaphore = _slots[loop] = asyncio.Semaphore(MAX_CONCURRENT_WORKFLOWS)
    return semaphore


def recover_interrupted() -> int:
    """Called once at start-up (see src/api/app.py lifespan)."""
    session = SessionLocal()
    try:
        return fail_stale(session, RECOVER_MAX_AGE_SECONDS)
    finally:
        session.close()
