# Diet Plan Service (multi-agent workflow)

FastAPI service that turns a user's profile into a one-day meal plan. Browsers call it **through the ASP.NET Core API** (`/api/diet/*`); the API passes each request on unchanged with the caller's token and the shared service key.

Objective: *compute safe calorie/macro targets for a profile, generate meals that fit them, verify the meals with fixed rules, and let the user save the result - after a Trainer/Admin has approved it when the profile is high risk.*

## Workflow

```
planner -> NutritionAnalystAgent -> MealGeneratorAgent -> SafetyValidatorAgent
validator: pass            -> done (low/medium risk: auto_approved, high risk: pending review)
           revise (max 1)  -> back to MealGeneratorAgent with the violations as feedback
           reject          -> rejected (nothing can be saved)
           retries used up -> returns the closest plan, marked "outside tolerance" (a reject-tier problem is never returned)
```

`POST /api/diet/generate` answers at once with a `workflowId`; the run continues in the background and the web app polls `GET /api/diet/workflows/{id}` to show each agent's real progress. `POST /api/diet/workflows/{id}/refine` applies one free-text edit to a finished plan (same start-now, poll-for-progress pattern).

| Agent | Input -> Output (`src/models/contracts.py`) | Tools (`src/tools/tool_registry.TOOL_PERMISSIONS`) | LLM |
|---|---|---|---|
| planner | objective + preferences -> `PlanResult` (the four steps, a `route`, the tools this run may call) | none | no |
| NutritionAnalystAgent | `NutritionAnalystInput` -> `NutritionAnalystOutput` (targets, risk level + flags, budget context) | `calculate_targets`, `assess_risk`, `lookup_budget` | no |
| MealGeneratorAgent | `MealGeneratorInput` -> `MealGeneratorOutput` (meals) | `generate_meals`, `refine_meals` | yes |
| SafetyValidatorAgent | `SafetyValidatorInput` -> `SafetyValidatorOutput` (verdict + violations) | `validate_plan` | no |

Only the meal generator uses the LLM. Calories and macros come from `src/tools/calculator.py` (Mifflin-St Jeor) and the model never computes them, so the numbers are reproducible and the model can only choose foods.

Controls: every tool call goes through `workflow.call_tool` (role allow-list from the registry, narrowing to the tools in the run's plan, Pydantic contract, timeout, trace event). The model's output is validated deterministically before the user sees it. Retries and the overall time budget (230 s) are bounded. Failures end in a recorded `failed`/`rejected` status with a plain-language message and nothing saved.

## Approval (high-risk plans)

`NutritionAnalystAgent` assigns a risk level (`low`, `medium`, `high`) from age, declared medical conditions and how steep the calorie deficit is. Only **high** risk needs a human:

- the run finishes `completed` with `approvalStatus: "pending"`;
- `POST /confirm` and `PUT /plans/{id}` answer **409** (plain-text `detail`) until a Trainer or Admin calls `POST /workflows/{id}/approve`; a rejected plan can never be saved;
- a decision is made once: a second one gets 409, and the status change is a single conditional `UPDATE`, so two reviewers cannot both win;
- the approver's id, role, note and time are stored (`approved_by`, `approver_role`, `approval_note`, `decided_at`) and shown in the trace;
- editing an approved high-risk plan (`refine`) sends it back to `pending`;
- old clients that save without a `workflowId` are checked against targets **recomputed on the server** (a client cannot dodge review by claiming a safe calorie figure).

Low and medium risk plans are `auto_approved` and behave exactly as before.

## Validator rules (deterministic, `src/utils/validators.py`)

The validator never uses an LLM. Every violation has a `severity` (`reject` or `revise`), the `target` agent that can fix it and whether a `retryable` attempt could help; the verdict follows from the severities.

| Group | Codes |
|---|---|
| Structure | `SCHEMA_INVALID` (reject) |
| Calories and macros | `CALORIE_OUT_OF_TOLERANCE` (revise within 50%, reject beyond), `MACRO_IMPLAUSIBLE`, `MEAL_COUNT_OUT_OF_BOUNDS`, `ITEM_CALORIES_OUT_OF_BOUNDS` |
| Restrictions | `RESTRICTION_VIOLATION` (reject for vegetarian, vegan, halal, dairy-free, lactose-intolerant, gluten-free, peanut allergy), `DISLIKE_MATCH` (revise) |
| Medical | `BELOW_SAFE_FLOOR` (reject), `DIABETES_SUGAR_RISK`, `SODIUM_RISK`, `FRIED_FAT_RISK` (revise) |
| Output safety | `OUTPUT_HAS_LINK_OR_MARKUP`, `OUTPUT_INJECTION` (revise once; if still present when retries run out the plan is rejected, never returned) |

Keyword matching is a substring test, so "catfish" is still caught for a vegetarian. Known-safe phrases that contain a restricted word (`almond milk`, `peanut butter`, `eggplant`, `graham`, `unsalted`, `sugar-free`, ...) are exempted per keyword; see `RESTRICTION_EXEMPT` and `MEDICAL_EXEMPT`.

## Prompt-injection guard (`src/utils/injection_guard.py`)

The service reads text anyone can influence: the `dislikes` note, the refine instruction, and the model's own output. A deterministic guard (no LLM) sits at each of those boundaries:

| Where | What it does |
|---|---|
| `dislikes` and refine `instruction` (`routes._guard_free_text`) | NFKC, zero-width and control characters removed, look-alike letters folded; a strong signal (override instructions, role lines, chat-template markers, tool coercion, verdict coercion, exfiltration, ...) is refused with **422** and a plain-text `detail`. Nothing is silently rewritten. |
| Prompts (`src/prompts/agent_prompts.py`) | User and model-derived text travels as JSON data; angle brackets are replaced so it cannot write a tag; the system prompt says these fields are never instructions. |
| Model output (`validators._check_output_safety`) | Meal names, portions and labels with a link, markup or instruction-like text are sent back for revision, and rejected if they persist. |
| Logs and the trace | Signal **codes only**, never the text (`guard_flags` on the planner event / step row). |

`DIET_INJECTION_MODE=monitor` detects and records without refusing, to check for false positives. Limits: pattern matching cannot catch every phrasing or language, so this lowers risk rather than removing it. What keeps a plan safe regardless are the fixed calculator targets, the deterministic validator, the human approval of high-risk plans and the database constraints.

## State (PostgreSQL, `src/models/db_models.py`)

| Table | Holds |
|---|---|
| `diet_plan_inputs`, `diet_plans` | what the user confirmed: the preferences and the saved plan |
| `diet_workflows` | one row per run: objective, `route`, plan, completed steps, targets, meals, validation results, events (trace), risk level, **approval fields**, final outcome, error, retry count. Check constraints on `status`, `approval_status`, `risk_level` |
| `diet_workflow_steps` | one row per agent/tool step: `seq`, agent, tool, ok, short error, duration, guard flag codes (FK -> workflow, cascade delete, unique `(workflow_id, seq)`) |

`src/agent/store.py` writes a step row in the **same transaction** as the workflow update that produced it, so the audit trail cannot disagree with the state. No prompts, model replies or secrets are stored. `src/utils/db_migrations.py` upgrades an existing database on start (adds the new columns; adds the check constraints as `NOT VALID`, enforced for every new and changed row without failing if an old row is odd).

Reliability (`src/agent/runner.py`, `src/agent/store.fail_stale`): on start-up any run left `running` by a restart is finished off (`failed` for a generation; back to `completed` with the plan unchanged for an interrupted edit). At most `DIET_MAX_CONCURRENT_WORKFLOWS` (default 3) runs use the LLM at once; the rest wait with status `running`, and the time budget starts only once a slot is free.

## Internal-only mode

Set `DIET_AGENT_KEY` (>= 32 random characters) and every `/api/diet` route also needs the header `X-Diet-Agent-Key` (constant-time compare), so only the ASP.NET API can call the service; a browser cannot. The caller's JWT is still verified here for identity, ownership and roles. Unset, the service behaves exactly as before (directly reachable with a JWT). A key that is set but too short fails closed with 503. `/health`, `/docs`, `/redoc` and `/openapi.json` stay open (for development). `DIET_ALLOWED_HOSTS` optionally restricts the `Host` header.

To switch it on: `dotnet user-secrets set "DietAgent:ServiceKey" "<value>"` in `VitroFit.API` (it starts this service as a sidecar and passes the key through the environment, so the two cannot drift apart), then point the web app at the API: `VITE_DIET_AGENT_API_URL=http://localhost:5284/api/diet`.

The API side is `BackendAPI/VitroFit.API/Features/DietAgent`: JWT, a per-user rate limit on `generate` and `refine` (`DietAgent:AiRequestsPerMinute`, default 20), a path allow-list, a body size limit, and a pass-through that returns the service's status and body unchanged.

## Logging (`src/utils/logger.py`)

One line per event with the workflow id, e.g. `tool end wf=1a2b3c4d agent=MealGeneratorAgent tool=generate_meals ok=True ms=1830`. Log lines are trusted output, so values are stripped of control characters and newlines, secrets are redacted, non-ASCII is replaced and everything is truncated. Prompts, model replies and user text are never logged. Level: `DIET_LOG_LEVEL`.

## Layout
```
main.py            entry point (`uvicorn main:app --port 8003`, how VitroFit.API launches it, or `python main.py`)
src/agent/         workflow.py (coordinator), runner.py (concurrency + recovery hook), store.py (audit mirror + recovery)
  nodes/           planner, nutrition_analyst, meal_generator, safety_validator
src/api/           app.py (FastAPI app, CORS, lifespan), routes.py (all /api/diet endpoints)
src/models/        db_models.py, schemas.py (request bodies), contracts.py (agent contracts), llm_client.py
src/prompts/       system_prompts.py, agent_prompts.py
src/tools/         tools.py (generate_meals / refine_meals), calculator.py, budget_reference.py, tool_registry.py
src/utils/         db.py, db_migrations.py, auth.py, security.py, validators.py, injection_guard.py, logger.py
tests/  tests/evaluation/  tests/perf/
```
Run tests from this directory (`pytest.ini` sets `pythonpath=.`, so imports are `src.<package>.<module>`).

## Setup

1. PostgreSQL running; set `DATABASE_URL` and `NVIDIA_API_KEY` in the shared `BackendAPI/.env` (copy `BackendAPI/.env.example`).
2. `python -m venv venv && venv/Scripts/pip install -r requirements.txt`
3. JWT settings are read from `../VitroFit.API/appsettings.json`, so the two services cannot end up with different secrets. Start it with the API (sidecar) or `uvicorn main:app --port 8003`.

## API (all under `/api/diet`, JWT required)

`POST /generate` - `GET /workflows/{id}` - `GET /workflows/{id}/trace` - `POST /workflows/{id}/refine` - `POST /confirm` - `GET /plans` - `PUT /plans/{id}` - `DELETE /plans/{id}` - `GET /approvals/pending` (Trainer/Admin) - `POST /workflows/{id}/approve` and `/reject?note=` (Trainer/Admin)

## Tests

```bash
pytest                      # everything, on SQLite, with the coverage gate (80%)
TEST_DATABASE_URL=postgresql+psycopg2://user:pw@localhost:5432/diet_test pytest   # real PostgreSQL: constraints, migrations
pytest -m evaluation        # only the agent golden cases (writes reports/evaluation_report.md)
pytest -m perf              # latency smoke tests
python tests/evaluation/mutation_check.py   # break 25 safeguards one by one; the suite must notice each
```

No test needs the network, an API key or a real model: the meal-generation tool and the model call are scripted, and a safety net in `tests/conftest.py` makes any attempt to reach the real LLM fail loudly. Tests never touch your development database (SQLite file by default).

| Layer | Where | What it proves |
|---|---|---|
| Unit | `test_validators*`, `test_injection_guard`, `test_planner_and_registry`, `test_tools`, `test_auth_and_reference` | validator rules and safe-phrase exemptions, the guard (attacks blocked, normal text untouched), planner/registry, the LLM tools with a scripted model, JWT handling, the calculator |
| Integration | `test_main_endpoints`, `test_workflow`, `test_approval_gating`, `test_reliability`, `test_internal_mode` | the real API, coordinator and database together: approval rules, audit rows, recovery, concurrency cap, migrations, internal-only mode |
| Agent evaluation | `tests/evaluation` (marker `evaluation`) | 20 golden cases, rule-based (no LLM judge), mapped to the assignment's ten criteria |
| Performance | `tests/perf` (marker `perf`) | the service's own overhead stays small (validator, guard, planner, a whole run with an instant model). Real-model latency has not been measured for this service |

CI (`.github/workflows/ci.yml`, job `diet-plan-service`) runs all of this on SQLite and on a real PostgreSQL for every push and pull request to `main` and `development`.
