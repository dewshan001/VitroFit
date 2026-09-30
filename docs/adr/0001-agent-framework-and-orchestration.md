# ADR-0001: Agent framework and orchestration method for the gym workflow

- **Status:** Draft for the group to review and adopt (the assignment requires the decision and its reasoning to be the group's own).
- **Date:** 2026-09-30
- **Scope:** `BackendAPI/GymAgentService`, the Agentic AI subsystem behind Find Gyms and the gym approval workflow.

## Context

The subsystem must take a domain objective ("collect verified equipment, classes and contact details for this gym and recommend four
workouts"), make a multi-step plan, delegate to **at least four distinct agents** (each with its own responsibility, input/output contract and
tool permissions), call only allow-listed tools, persist its state, validate results **deterministically**, **pause for a human decision** before
anything is published as verified, and leave an audit trail (assignment section 9.1).

The first version was one ReAct agent that could call every tool, followed by a separate single LLM call for workouts. It had no approval step,
its confidence check was dead code, and its state lived in memory. Constraints: free or institution-provided models only (NVIDIA NIM or
OpenRouter free tier), the public API must stay ASP.NET Core, the team already knows LangGraph from the labs, and a paused approval must survive
a service restart.

## Options considered

| Option | For | Against |
|---|---|---|
| A. One ReAct agent with all tools (the original) | Least code | Not four distinct agents; the model decides which tool to use with no least-privilege boundary; no place for deterministic validation or a pause |
| **B. LangGraph `StateGraph`: four agents as nodes, deterministic planner and validator, `interrupt()` for approval, Postgres checkpointer** | Explicit graph (delegation and retries are visible and testable); built-in interrupt/resume with durable checkpoints; known to the team; Python ecosystem for the tools we use (web search, vector store) | Ties us to LangGraph and its checkpointer versions; adds a Python process next to the .NET API |
| C. Hand-written coordinator (as the Diet plan service on another branch) | Full control, no framework | We would have to build durable pause/resume, tracing and the graph semantics ourselves |
| D. Microsoft Agent Framework, LlamaIndex agents or Google ADK | Capable frameworks; Microsoft's runs on .NET | Nobody in the group has used them; our tools and vector store are Python; no time to prototype |

Options C and D were compared by reasoning, not by building and measuring them.

## Decision

Use **B**. Concretely:

- Four agents, each with a Pydantic contract that forbids unknown fields (`contracts.py`) and a tool allow-list enforced in one place (`tool_registry.py`):
  **planner** (no tools, no LLM: a deterministic plan and route), **gym analysis** (scrape, search, similar-gym lookup; LLM), **workout recommendation**
  (a read-only taxonomy tool; LLM), **validator/safety** (no tools, no LLM: schema, business rules, URL allow-list, injection checks).
- Only two agents use an LLM. The planner and the validator are plain code, so the plan and the verdict are reproducible and cheap to test.
- Validation failures are routed back to the agent named in the violation (at most 2 revisions), then end in a recorded safe failure.
- The approval step calls `interrupt()`; the run waits in the Postgres checkpointer until an Admin or Gym_Owner approves, rejects or requests a
  revision. Only "approve" continues to publishing.
- The service is internal: ASP.NET Core authenticates users, checks roles and rate-limits, then calls it with a shared service key.

## Consequences

**Good (with evidence).**
- Each requirement in section 9.1 maps to code and a test. The agent evaluation runs 21 golden cases (115 rule-based checks) covering the ten assignment
  criteria; 21 deliberate faults injected into the code were all caught by those cases alone (`docs/evaluation/gym-agent-evaluation-report.md`).
- Pause and resume were tested across a restart on a real PostgreSQL. The full pytest suite passes on SQLite (557 passed, 5 skipped) and on PostgreSQL
  (562 passed); coverage is 82.5% and 83.9%, gated at 80%.
- Our own code is not the slow part. Guard, validator and planner take about 3.5 ms together; the two LLM agents take 95.8% of a run's time
  (gym analysis 61.0 s and workout recommendation 30.9 s at p50, from a few stored runs). See `docs/performance/gym-agent-latency.md`.
- Least privilege is structural: an agent can only reach tools its role and the plan allow, and hostile text is neutralised before any model sees it.

**Costs and risks.**
- Dependency coupling: the checkpointer package is pinned (`langgraph-checkpoint-postgres==3.1.2`); a fresh install resolved LangGraph 1.2.12 and the suite
  still passed, but upgrades need a test run.
- One more process and an internal HTTP hop between ASP.NET and the agents, and the first use of the embedding model after a start costs about 9 s (measured).
- More code than a single ReAct agent, and the injection guard is pattern-based, so it lowers risk without removing it; the validator, approval step and database
  constraint remain the safety net.
- Real-model answer quality is not covered by the golden cases (the model is scripted there).

**Revisit if** agents need to negotiate or branch in parallel, if throughput ever matters (the service levelled off at about 18 workflows per second on the development
machine), or if an in-process .NET agent framework becomes attractive to the group.
