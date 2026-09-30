# Architecture Decision Records

One short record per key technical decision (context, options considered, decision, consequences), as required by
section 14.2 of the assignment. Status **Draft** means the group has not yet reviewed and adopted it.

| # | Decision | Status |
|---|---|---|
| [0001](0001-agent-framework-and-orchestration.md) | Agent framework and orchestration method for the gym workflow (LangGraph, four agents, deterministic validator, `interrupt()` approval) | Draft |
| [0002](0002-workflow-state-schema.md) | Database schema strategy for agent workflow state (normalised tables plus the checkpointer, constraint on `verified`) | Draft |

Still to be recorded by the group, as the assignment requires: the state-management approach in React and in Flutter, and the cloud deployment platform.

Evidence the records cite: `docs/evaluation/gym-agent-evaluation-report.md` (agent evaluation), `docs/performance/gym-agent-latency.md` (latency and load),
and the test suite in `BackendAPI/GymAgentService/tests`. Alternatives are compared by reasoning unless a record says it measured them.
