# ADR-0003: Orchestration method for the diet-plan workflow

- **Status:** Draft for the group to review and adopt (the assignment requires the decision and its reasoning to be the group's own).
- **Date:** 2026-10-04
- **Scope:** `BackendAPI/DietPlanService`, the agentic subsystem behind the Diet Plans page, and its public entry in `VitroFit.API/Features/DietAgent`.

## Context

The diet workflow has the same obligations as the gym workflow (ADR-0001): a domain objective, a plan, at least three distinct agents with their own contracts and tool permissions, allow-listed tools, durable state, **deterministic** validation, a **human decision** before anything risky is accepted, and an audit trail.

It started as a hand-written coordinator (`workflow.py`): a fixed list of steps, a revise loop, and state saved to one table after every step. ADR-0001 compared that style ("Option C") with LangGraph for the gym service and chose LangGraph because the gym run has to *pause* for an approval and survive a restart. The diet workflow does not: it is short (about one to two minutes, one LLM call plus at most one retry), it ends on its own, and the user is waiting on the page for it, so there is nothing to resume. The question here is whether it should adopt LangGraph for consistency, or keep the coordinator and add the controls the gym service has.

Constraints: the public API stays ASP.NET Core; the web app polls `GET /workflows/{id}` and reads fixed JSON shapes and plain-text `detail` errors, which must not change; free or institution-provided models only; the team owns this service and wants it explainable step by step.

## Options considered

| Option | For | Against |
|---|---|---|
| A. Keep the hand-written coordinator as is | No change | Missing controls the gym service has: approval is only a label, no recovery after a restart, no injection guard, no audit table, no CI |
| **B. Keep the coordinator, add the gym service's controls in plain Python** | Same safety properties where they matter; no new dependency or checkpointer to run and pin; every behaviour the web app relies on stays byte-for-byte; the code reads top to bottom | We maintain the loop and the approval gate ourselves instead of getting `interrupt()` and checkpoints from a framework |
| C. Move to a LangGraph `StateGraph` with `interrupt()` | Same orchestration as the gym service; a paused run could resume after a restart | Needs the Postgres checkpointer and its version pinning for a run that never needs to pause; rewrites the progress/polling contract the web app depends on; high-risk approval does not need to resume a *running* graph, only to gate the *save* |

Options were compared by reasoning, not by building and measuring them.

## Decision

Use **B**. Concretely:

- Keep the three agents with strict Pydantic contracts (`src/models/contracts.py`) and add a deterministic **planner** (no LLM) that fixes the step list, chooses a route (`standard` / `medical_review`) and narrows the tools a run may call. The allow-lists live in one place (`src/tools/tool_registry.py`) and are enforced by `workflow.call_tool`.
- Only the meal generator uses the LLM. Targets come from the calculator; the validator is plain code.
- **Approval is enforced at the point that matters, saving.** A high-risk plan is `pending` and `POST /confirm` / `PUT /plans/{id}` refuse it (409) until a Trainer/Admin approves; a decision is made once, with a conditional `UPDATE`; editing an approved plan resets it; old clients without a `workflowId` are judged on server-recomputed targets.
- Safety layers that do not depend on the framework: an input and output **prompt-injection guard**, validator rules with a `target` agent and `retryable` flag, bounded retries and time budget, database check constraints, and an audit table written in the same transaction as the state.
- Operability: start-up recovery of interrupted runs, a cap on concurrent LLM runs, structured safe logging.
- Access: ASP.NET Core authenticates, rate-limits and passes requests through with a shared service key (`DIET_AGENT_KEY`); the service still verifies the JWT for identity and roles. The key is optional, so rollout does not break the existing direct path.

## Consequences

**Good (with evidence).**
- Every requirement in the assignment's section 9.1 maps to code and a test. The evaluation runs 20 golden cases (87 rule-based checks) covering the ten criteria (`docs/evaluation/diet-agent-evaluation-report.md`); 25 deliberate faults injected into the code were all noticed by the test suite (`tests/evaluation/mutation_check.py`).
- 234 service tests pass on SQLite and on PostgreSQL (coverage 96%, gated at 80%); 56 .NET tests cover the proxy.
- The web app needed one additive change (sending `workflowId` when saving) plus a URL; all response shapes and statuses are unchanged.
- A restart can no longer leave a run `running` forever, and one user cannot start unlimited LLM runs.

**Costs and risks.**
- We own the retry loop and the approval gate. They are small and tested, but a framework would give a durable pause for free. If a future requirement needs a run to wait for a human *before finishing* (rather than before saving), revisit Option C.
- The injection guard is pattern-based: it lowers risk without removing it. The validator, the fixed targets, the approval of high-risk plans and the constraints remain the safety net.
- Keyword matching in the validator is a substring test with an exemption list; new foods can still produce a false alarm (a plan is revised, not harmed) until added to the list.
- High-risk users cannot save until a Trainer/Admin acts through the API; there is no review screen in the web app yet.
- Real-model answer quality and latency are not covered by the golden cases (the model is scripted there) and have not been measured for this service.
