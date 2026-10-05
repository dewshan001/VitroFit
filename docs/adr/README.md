# Architecture Decision Records

One short record per key technical decision (context, options considered, decision, consequences), as required by
section 14.2 of the assignment. Status **Draft** means the group has not yet reviewed and adopted it.

| # | Decision | Status |
|---|---|---|
| [0001](0001-agent-framework-and-orchestration.md) | Agent framework and orchestration method for the gym workflow (LangGraph, four agents, deterministic validator, `interrupt()` approval) | Draft |
| [0002](0002-workflow-state-schema.md) | Database schema strategy for agent workflow state (normalised tables plus the checkpointer, constraint on `verified`) | Draft |
| [0003](0003-diet-plan-agent-orchestration.md) | Orchestration method for the diet-plan workflow (hand-written coordinator plus the gym service's controls, approval at save, .NET pass-through) | Draft |

Still to be recorded by the group, as the assignment requires: the state-management approach in React and in Flutter, and the cloud deployment platform.

Evidence the records cite: `docs/evaluation/gym-agent-evaluation-report.md` and `docs/evaluation/diet-agent-evaluation-report.md` (agent evaluation), `docs/performance/gym-agent-latency.md` (latency and load),
and the test suites in `BackendAPI/GymAgentService/tests` and `BackendAPI/DietPlanService/tests`. Alternatives are compared by reasoning unless a record says it measured them.
