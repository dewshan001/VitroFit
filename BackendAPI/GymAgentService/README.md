# Gym Agent Service (multi-agent workflow)

Internal FastAPI + LangGraph service. **Only ASP.NET Core calls it** (`/api/gym-agent/workflows`); React and Flutter never do.

## Workflow

Objective: *collect verified equipment, classes and contact details for a gym and recommend four workouts, then publish as `verified` only after a Gym_Owner/Admin approves.*

```
planner → gym_analysis → workout_recommendation → validator
validator: pass → approval_gate (interrupt) → publish
           revise (max 2) → back to the agent named in the violation
           reject / exhausted → safe_fail
approval_gate: approve → publish | reject → end | revise (max 2) → workout_recommendation
```

| Agent | Input → Output (`contracts.py`) | Tools (`tool_registry.TOOL_PERMISSIONS`) | LLM |
|---|---|---|---|
| planner | `PlannerInput` → `Plan` | none | no |
| gym_analysis | `AnalysisInput` → `GymFacts` (+ evidence) | `scrape_gym_website`, `search_gym_info`, `lookup_similar_gyms` (narrowed by the plan) | yes |
| workout_recommendation | `RecommendInput` → `Recommendations` | `list_equipment_taxonomy` (offline, read-only) | yes |
| validator | `ValidatorInput` → `Verdict` | none | no |

Controls: every tool call goes through `call_tool` (role allow-list, plan narrowing, input schema, scrape only the gym's own public host, timeout, sanitised output). Contact details must be backed by a snippet found in the retrieved text. Scraped text and reviewer feedback are treated as untrusted. Retries and time budget are bounded. Failures end in `safe_fail` with nothing published.

State: LangGraph `AsyncPostgresSaver` (`thread_id = workflow id`, so a paused approval survives restarts) plus tables `gym_agent_workflows` (plan, steps, tool results, validation results, errors, approval, outcome) and `gym_agent_events` (one row per agent/tool step with timing). No prompts, reasoning or secrets are stored.

## Setup and startup order

1. PostgreSQL running; `cp .env.example .env` and set `DATABASE_URL`, an LLM key (`NVIDIA_API_KEY` or `OPENROUTER_API_KEY`), and `GYM_AGENT_KEY` (≥ 32 random chars).
2. `python -m venv venv && venv/Scripts/pip install -r requirements.txt`
3. Start the API with the same key: `dotnet user-secrets set "GymAgent:ServiceKey" "<same value>"` (the API also starts this service as a sidecar via `python server.py` and passes the key through the environment). Manual start: `python server.py` (uses a selector event loop, required by the Postgres checkpointer on Windows).

The legacy `/api/gyms/details` and `/api/gyms/workouts` endpoints still exist for the current clients and are **deprecated**; remove them (and `enrichment_agent.py`, `workout_agent.py`) once the clients use the ASP.NET routes.

## Internal API (header `X-Gym-Agent-Key`)

`POST /internal/workflows` · `GET /internal/workflows[?status=&requestedBy=]` · `GET /internal/workflows/{id}` · `GET /internal/workflows/{id}/events` · `POST /internal/workflows/{id}/decision`

## Tests

`venv/Scripts/python -m pytest` (no network, database server or paid model needed: SQLite, in-memory checkpointer, scripted model).
