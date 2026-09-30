# ADR-0002: Database schema strategy for agent workflow state

- **Status:** Draft for the group to review and adopt (the assignment requires the decision and its reasoning to be the group's own).
- **Date:** 2026-09-30
- **Scope:** how `BackendAPI/GymAgentService` stores workflow state, approvals and audit data in PostgreSQL.

## Context

The assignment requires the workflow ID, objective, plan, completed steps, tool results, validation results, errors, approval status and final outcome to
be persisted "in structured, durable storage" (section 9.1), stored as execution summaries only, never hidden reasoning, passwords or tokens (section 6).
More specifically we need: a paused approval that survives a restart; an audit trail an administrator can read (what each agent and tool did, how long it
took, who decided and when); a database-level guarantee that nothing becomes `verified` without an approved workflow behind it; and a schema that fits the
ER diagram. LangGraph's own checkpointer stores the graph state, but as opaque serialised blobs.

## Options considered

| Option | For | Against |
|---|---|---|
| A. Checkpointer tables only | Nothing to design; durable; resume works | Not queryable or auditable; no constraints; can not answer "which tools ran and how long" without decoding blobs |
| B. One JSONB document per workflow in a single table | Simple; one read | Steps and tool calls can not be queried, constrained or indexed; the whole document is rewritten on every update; no foreign keys |
| **C. Normalised tables plus the checkpointer, in the application database** | Queryable audit trail; real constraints and foreign keys; each agent step recorded atomically with the state change; the same database as the gyms, so a foreign key can link verified data to its approval | More tables to migrate; two stores to keep consistent |
| D. A separate database or schema for agent data | Isolation | No cross-database foreign key, so the "verified only through an approved workflow" rule could not be enforced by the database |

## Decision

Use **C**. The tables:

- `gym_agent_workflows`: one row per run with the state and approval fields (`status`, `approval_status`, `approved_by`, `approver_role`, `approval_note`, `decided_at`,
  `final_outcome`, `retry_count`), and JSONB for the variable-shaped parts read as a whole (`request`, `plan`, `facts`, `recommendations`, `validation_results`, `errors`).
  Check constraints limit `status` and `approval_status` to the allowed values.
- `gym_agent_steps`: one row per agent run (`seq`, `agent`, `summary`, `ok`, `error`, `duration_ms`), unique on `(workflow_id, seq)`, cascading delete.
- `gym_agent_tool_calls`: one row per tool call (`tool`, input summary, `ok`, `error_code`, `guard_flags`, `duration_ms`), with foreign keys to the workflow and to its step.
- `gym_agent_details` gains `verified_workflow_id` (foreign key, `ON DELETE RESTRICT`), `verified_by`, `verified_at` and a CHECK constraint:
  `source <> 'verified' OR verified_workflow_id IS NOT NULL`.
- The LangGraph Postgres checkpointer keeps the resumable graph state under `thread_id = workflow id`.

Rules that keep the two stores honest: a node's step row, its tool-call rows and the workflow state update are written in **one transaction**; publishing re-reads the
approval from the workflow row and refuses unless that row records an approval by an approver role, so the tables, not the checkpoint, decide what may be published.
Only summaries are stored (no prompts, model reasoning, tokens or credentials); NUL characters are stripped before any write because PostgreSQL cannot store them.

## Consequences

**Good (with evidence).**
- Database operations are cheap on PostgreSQL (median, same machine): recording a step with two tool calls and the state update 2.6 ms, reading a workflow with its
  steps and tool calls 1.5 ms, the event timeline 1.1 ms, publishing 3.1 ms, reading a paused checkpoint 0.78 ms (`docs/performance/gym-agent-latency.md`).
- The guarantees are enforced by the database, not only by code, and tested on a real PostgreSQL: a verified row without a workflow is refused, a workflow that vouches
  for data can not be deleted, step numbers are unique, invalid statuses are refused, a step and its state change commit or fail together, and the schema upgrade
  (columns, backfill, constraint) is idempotent and runs on an old database.
- The administrator's approval page reads the same tables (steps, tool calls, flags, approval fields), so the audit trail and the UI can not drift apart.

**Costs and risks.**
- Two stores (tables and checkpoint) must stay consistent. We mitigate it by making the tables authoritative for decisions and the checkpoint only for resuming, but a bug
  could still leave them disagreeing; the recovery step marks crashed runs as failed and keeps paused ones.
- Schema changes are hand-written idempotent SQL in `db_migrations.py`, not a migration tool; the new provenance constraint was added as `NOT VALID`, so a legacy verified row
  set by hand would not be re-checked (a warning is logged for such rows).
- The JSONB columns have no database-level shape check; the Pydantic contracts validate them in the application.
- The list endpoint returns complete rows, so it is the heaviest HTTP call (12.8 ms p50 for 50 rows against 3.0 ms for one workflow); a summary-only list would be cheaper.
- Rows are never pruned yet, and the checkpoint keeps the sanitised web text the agents read (public content, no prompts or reasoning).

**Revisit if** the number of runs grows enough to need retention or partitioning, if the group adopts a migration tool for the whole solution, or if the two-store
consistency ever causes an incident.
