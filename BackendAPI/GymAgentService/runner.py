"""Runs gym workflows in the background and applies human approval decisions.

`start` creates the durable row and launches the graph. The graph pauses at the
approval interrupt (state lives in the checkpointer + workflow row, so a restart does
not lose it). `decide` verifies the approver, atomically claims the paused run, and
resumes it with the decision.
"""

import asyncio
import logging
import os

from langgraph.types import Command

from contracts import APPROVER_ROLES, ApprovalDecision, PlannerInput
from store import WorkflowStore

logger = logging.getLogger("gym_agent")

WORKFLOW_BUDGET_SECONDS = float(os.getenv("GYM_WORKFLOW_BUDGET_SECONDS", "240"))


class NotFound(Exception):
    pass


class Conflict(Exception):
    pass


class WorkflowRunner:
    def __init__(self, store: WorkflowStore, graph, budget_seconds: float = WORKFLOW_BUDGET_SECONDS):
        self.store = store
        self.graph = graph
        self.budget = budget_seconds
        self._tasks: set[asyncio.Task] = set()

    # ── lifecycle ───────────────────────────────────────────────────────

    async def recover(self) -> int:
        """Fail runs a crash left in 'Running'. Paused (AwaitingApproval) runs are kept."""
        return await asyncio.to_thread(self.store.fail_stale, int(self.budget) + 60)

    async def drain(self) -> None:
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    # ── commands ────────────────────────────────────────────────────────

    async def start(self, request: PlannerInput, requested_by: str) -> str:
        payload = request.model_dump(mode="json")
        workflow_id = await asyncio.to_thread(self.store.create, payload, requested_by)
        initial = {
            "workflow_id": workflow_id,
            "request": payload,
            "status": "Running",
            "revisions": 0,
            "human_revisions": 0,
            "corpus": [],
        }
        self._spawn(self._drive(workflow_id, initial))
        return workflow_id

    async def decide(self, workflow_id: str, decision: ApprovalDecision) -> dict:
        if decision.actor_role not in APPROVER_ROLES:
            raise PermissionError("Only Gym_Owner or Admin may decide")
        row = await asyncio.to_thread(self.store.get, workflow_id)
        if row is None:
            raise NotFound(workflow_id)
        if row["status"] != "AwaitingApproval":
            raise Conflict(f"Workflow is {row['status']}, not awaiting approval")
        snapshot = await self.graph.aget_state(self._config(workflow_id))
        if not snapshot.next:
            raise Conflict("No paused approval step exists for this workflow")
        if not await asyncio.to_thread(self.store.claim, workflow_id, "AwaitingApproval", "Running"):
            raise Conflict("Another decision is already being applied")
        self._spawn(self._drive(workflow_id, Command(resume=decision.model_dump(mode="json"))))
        return {"id": workflow_id, "status": "Running", "decision": decision.decision}

    # ── internals ───────────────────────────────────────────────────────

    @staticmethod
    def _config(workflow_id: str) -> dict:
        # metadata reaches the logging handler, so every model and tool log line carries the run id
        return {"configurable": {"thread_id": workflow_id}, "recursion_limit": 40, "metadata": {"workflow_id": workflow_id}}

    def _spawn(self, coro) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _drive(self, workflow_id: str, graph_input) -> None:
        try:
            await asyncio.wait_for(
                self.graph.ainvoke(graph_input, self._config(workflow_id)), timeout=self.budget
            )
        except asyncio.TimeoutError:
            await self._fail(workflow_id, "TIMEOUT")
        except Exception as exc:
            logger.exception("Workflow %s crashed", workflow_id)
            await self._fail(workflow_id, type(exc).__name__[:60] or "INTERNAL_ERROR")

    async def _fail(self, workflow_id: str, code: str) -> None:
        delta = {
            "status": "Failed",
            "final_outcome": f"Workflow stopped safely ({code}); nothing was published.",
            "errors": [{"agent": "runner", "code": code}],
        }
        try:
            await asyncio.to_thread(
                self.store.record_node,
                workflow_id,
                "runner",
                ok=False,
                duration_ms=0,
                error=code,
                summary=delta["final_outcome"],
                tool_calls=[],
                delta=delta,
            )
        except Exception:
            logger.exception("Could not record failure for workflow %s", workflow_id)
