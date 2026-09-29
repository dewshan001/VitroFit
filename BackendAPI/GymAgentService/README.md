# Gym Agent Service (multi-agent workflow)

Internal FastAPI + LangGraph service. **Only ASP.NET Core calls it**; React and Flutter never do. Clients use `/api/gyms/*` and `/api/gym-agent/workflows/*` on the API, where JWT and roles are enforced.

## Internal-only

- Every route except `/health` requires the shared `X-Gym-Agent-Key` header (>= 32 chars, constant-time compare). No key configured = every request gets 503 (fail closed).
- `server.py` binds to `127.0.0.1` only. Requests must be addressed to `127.0.0.1`/`localhost` (`GYM_ALLOWED_HOSTS`), which blocks DNS-rebinding style access from a browser.
- No CORS middleware, so a browser cannot call it. No `/docs`, `/redoc` or `/openapi.json`.
- Routes: `/internal/gyms/{details,workouts}` and `/internal/workflows/...`.
- ASP.NET adds JWT, roles, per-user rate limiting, input validation and per-call timeouts (AI calls 150 s, others 30 s) in front.

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

State (all in PostgreSQL): LangGraph `AsyncPostgresSaver` (`thread_id = workflow id`, so a paused approval survives restarts) plus normalised tables:

| Table | Holds |
|---|---|
| `gym_agent_workflows` | objective, request, plan, facts, recommendations, validation results, errors, status, **approval fields** (`approval_status`, `approved_by`, `approver_role`, `approval_note`, `decided_at`), final outcome, retry count |
| `gym_agent_steps` | one row per agent/node run: `seq`, agent, summary, ok, error, duration (FK → workflow, unique `(workflow_id, seq)`, cascade delete) |
| `gym_agent_tool_calls` | one row per tool call: agent, tool, input summary, ok, error code, duration (FK → workflow and → step, cascade delete) |

A node's step, tool calls and workflow update are written in one transaction, so the audit trail can never disagree with the state. No prompts, reasoning or secrets are stored. Status and approval values are protected by check constraints.

Admins (and Gym_Owners) review runs on the React page `/admin/gym-approvals`, backed by `/api/gym-agent/workflows/*`.

Flow: on **Find Gyms**, an Admin/Gym_Owner clicks *Submit for verification* on a card → a workflow starts (a second click while one is active shows *Already under review*) → the run appears in **Gym Approvals** → *Approve* publishes it as `verified` → after a reload the Find Gyms card shows *Verified by gym* (the legacy details endpoint returns `verified` rows unchanged).

## How data becomes `verified`

AI output never becomes `verified` on its own. Four independent layers enforce this:

1. **Graph**: `approval_gate` calls LangGraph `interrupt()`. The run pauses (state in the Postgres checkpointer) until an Admin or Gym_Owner approves, rejects or requests a revision. Only *approve* continues to `publish`.
2. **`store.publish(workflow_id)`** is the only code that writes `source='verified'`. It does not trust its caller: in one transaction it locks the workflow row and refuses unless that row records an approval by an approver role, and it publishes exactly the facts and workouts stored on that row.
3. **Database**: `gym_agent_details` has `verified_workflow_id` (FK, `ON DELETE RESTRICT`), `verified_by`, `verified_at`, and `CHECK (source <> 'verified' OR verified_workflow_id IS NOT NULL)`. PostgreSQL itself refuses a verified row that has no approving workflow, and the workflow that vouches for it cannot be deleted.
4. **`/internal/gyms/details`** can only write `ai-*` sources and updates with `WHERE source <> 'verified'`, so it can neither create verified data nor overwrite it, even if an approval lands while it is running.

`db_migrations.py` upgrades an existing database on start: it adds the columns, links existing verified rows to their latest `Published` workflow, and adds the constraint as `NOT VALID` (enforced for all new and changed rows, without failing if a legacy row was verified by hand and has no workflow; a warning is logged for such rows).

## Prompt-injection guard (`injection_guard.py`)

The service reads text anyone can influence: scraped pages, web-search results, OpenStreetMap gym names and addresses, reviewer notes, and the model's own output. A deterministic guard (no LLM) sits at each of those boundaries:

| Where | What it does |
|---|---|
| Tool output (`tool_registry.call_tool`, and the legacy `tools.guarded`) | Normalises the text (Unicode NFKC, zero-width and control characters removed, look-alike letters folded), removes the sentences that try to instruct the model, and **withholds the whole source** (`INJECTION_BLOCKED`) when the evidence is strong. The model never sees a withheld source. |
| Tool arguments the model chooses | A search query cannot carry a URL, an encoded blob or instructions out of the system (`INVALID_INPUT`). |
| Request fields (gym name, address, known contacts) | Normalised on entry; a field that reads like an instruction ends the run in the planner step, before any model is called (`REQUEST_REJECTED` / `REQUEST_CONTENT_SUSPICIOUS`). |
| Prompt fence | Angle brackets inside untrusted text are replaced, so no text can write a closing `</untrusted_source>` and break out. |
| Model output (validator) | `OUTPUT_INJECTION`, `OUTPUT_HAS_LINK_OR_MARKUP` and `PROMPT_LEAK` send it back for revision. |
| Storage | NUL bytes are stripped everywhere (PostgreSQL cannot store them). |

Findings are stored on the tool call (`gym_agent_tool_calls.guard_flags`, codes only, never the text), shown to the approver on the Gym Approvals page, and logged as `prompt-injection signal source=... codes=...`. Set `GYM_INJECTION_MODE=monitor` to detect and record without changing anything (useful to check for false positives); tune the withholding threshold with `GYM_INJECTION_BLOCK_SCORE`.

Limits: pattern matching cannot catch every phrasing or language, so this reduces risk rather than removing it. What keeps the system safe regardless are the allow-listed tools and URLs, the deterministic validator, the human approval step and the database constraint on `verified`.

## Logging (`callbacks.py`)

`GymAgentLoggingHandler` is attached to every model (`llm_config.get_llm`) and every tool call, and logs one line per event with the workflow id and graph node, e.g. `llm end wf=1a2b3c4d node=gym_analysis ms=1830 tokens=612`. Log lines are trusted output, so they never contain prompts, model replies, page content or secrets: values are stripped of control characters and newlines, secrets are redacted, non-ASCII is replaced (safe on any console) and everything is truncated. Level: `GYM_LOG_LEVEL`.

## Validator rules (deterministic, `validators.py` + `url_policy.py`)

The validator never uses an LLM. Every violation has a `severity` and names the agent that should fix it; the verdict follows from the severities.

- **reject**: retrying cannot help (`REQUEST_WEBSITE_INVALID`, `NO_USABLE_DATA`). The run stops with a recorded safe failure.
- **revise**: the agent can fix its output. The violations are sent back to that agent (max 2 retries); a run still failing after that ends in `safe_fail` listing the codes.

| Group | Codes |
|---|---|
| URL allow-list | `EVIDENCE_URL_MISSING`, `EVIDENCE_URL_INVALID`, `EVIDENCE_URL_NOT_ALLOWED`, `EVIDENCE_URL_NOT_RETRIEVED`, `REQUEST_WEBSITE_INVALID` |
| Evidence and contacts | `UNSUPPORTED_ITEMS`, `UNSUPPORTED_CONTACT`, `INVALID_FORMAT`, `LOW_CONFIDENCE` |
| Business rules | `NO_EQUIPMENT_OR_CLASSES`, `NO_USABLE_DATA`, `DUPLICATE_ITEMS`, `TOO_MANY_ITEMS`, `INVALID_ITEM` |
| Workouts and safety | `WRONG_COUNT`, `DUPLICATE_NAME`, `DURATION_RANGE`, `BAD_CATEGORY`, `BAD_DIFFICULTY`, `UNKNOWN_EQUIPMENT`, `UNSAFE_CONTENT`, `BEGINNER_TOO_LONG`, `BEGINNER_TOO_INTENSE` |

A `source_url` only counts as support when it is a public https URL (http only on the gym's own host; no credentials, odd ports or internal/IP addresses), its host is the gym's own site or in `GYM_URL_ALLOWLIST` (matched on a domain boundary, so `evilfacebook.com` does not match `facebook.com`), and the page was actually retrieved in this run (scraped URL or a search-result `Source:`). Claims backed only by other URLs are reported as unsupported.

## Setup and startup order

1. PostgreSQL running; `cp .env.example .env` and set `DATABASE_URL`, an LLM key (`NVIDIA_API_KEY` or `OPENROUTER_API_KEY`), and `GYM_AGENT_KEY` (≥ 32 random chars).
2. `python -m venv venv && venv/Scripts/pip install -r requirements.txt`
3. Start the API with the same key: `dotnet user-secrets set "GymAgent:ServiceKey" "<same value>"` (the API also starts this service as a sidecar via `python server.py` and passes the key through the environment). Manual start: `python server.py` (uses a selector event loop, required by the Postgres checkpointer on Windows).

`/internal/gyms/details` and `/internal/gyms/workouts` are the single-agent enrichment used by Find Gyms (`enrichment_agent.py`, `workout_agent.py`). They can only write `ai-*` data; `verified` needs an approved workflow.

## Internal API (header `X-Gym-Agent-Key`)

`POST /internal/gyms/details` · `POST /internal/gyms/workouts` · `POST /internal/workflows` · `GET /internal/workflows[?status=&requestedBy=]` · `GET /internal/workflows/{id}` · `GET /internal/workflows/{id}/events` · `POST /internal/workflows/{id}/decision`

## Tests

`venv/Scripts/python -m pytest` (no network, database server or paid model needed: SQLite, in-memory checkpointer, scripted model).

Against a real PostgreSQL test database (also exercises the Postgres checkpointer and schema): create an empty database, then `TEST_DATABASE_URL=postgresql+psycopg2://user:pw@localhost:5432/gym_test venv/Scripts/python -m pytest`.
