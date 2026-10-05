# VitroFit

Fitness platform with an ASP.NET Core (.NET 10) Web API, five Python (FastAPI) services (four AI agents plus a chatbot), a React (Vite) web app and a Flutter mobile app.

**This is the only README.** Everything needed to install, configure, run, test and understand the project is here. There is also exactly one backend environment file (`BackendAPI/.env`) and one Python requirements file (`BackendAPI/requirements.txt`).

---

## Table of Contents

- [Tech Stack](#tech-stack)
- [Architecture and Services](#architecture-and-services)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Quick Start (first run)](#quick-start-first-run)
- [Configuration](#configuration)
- [Running the Python Services](#running-the-python-services)
- [The AI Agents](#the-ai-agents)
  - [Diet Plan agent](#diet-plan-agent-port-8003)
  - [Fitness agent](#fitness--workout-agent-port-8002)
  - [Gym Finding agent](#gym-finding-agent-port-8001)
  - [Time Management agent and timetable verification](#time-management-agent-port-8004-and-timetable-verification)
  - [Chatbot](#chatbot-port-8000)
- [Mobile App](#mobile-app)
- [API Endpoints](#api-endpoints)
- [Tests and CI](#tests-and-ci)
- [Default Admin Account](#default-admin-account)
- [Troubleshooting](#troubleshooting)
- [Other Documentation](#other-documentation)

---

## Tech Stack

| Layer | Technology |
| ----- | ---------- |
| Backend | ASP.NET Core (.NET 10), Entity Framework Core, PostgreSQL (Npgsql), JWT Bearer auth, Swagger/OpenAPI, MailKit (SMTP), Cloudinary (image hosting) |
| Web | React 19, Vite 8, React Router 7, Three.js (react-three-fiber / drei), GSAP, Framer Motion |
| Mobile | Flutter (Dart 3.12+), Provider, go_router, Dio, flutter_secure_storage, Google Maps, geolocator |
| Python services | FastAPI + Uvicorn, SQLAlchemy / psycopg, LangGraph with PostgreSQL checkpoints (Gym, Fitness, Time), a hand-written coordinator (Diet), ChromaDB + sentence-transformers (Gym). LLM providers: NVIDIA NIM (chatbot, Diet, Gym by default) and OpenRouter (Fitness, Time, Gym optional) |

---

## Architecture and Services

```
React web  --\                                  /-> GymAgentService        :8001  (LangGraph, internal only)
              >--> VitroFit.API (ASP.NET) :5284 -> DietPlanService         :8003
Flutter app --/        |                        \-> FitnessAgentService     :8002  (LangGraph, internal only)
                       |                         -> TimeManagementAgentService :8004 (LangGraph, internal only)
                       v                         -> chatbot_service         :8000  (also called by the clients directly)
                  PostgreSQL :5432
```

Clients call the .NET API, which checks the JWT, the role, the rate limit and the input, then forwards AI work to the right Python agent with a shared service key. The only exception is the chatbot, which both clients call directly (no login needed).

| Service | Port | Framework | LLM | Started by `dotnet run`? | Health check |
| ------- | ---- | --------- | --- | ------------------------ | ------------ |
| VitroFit.API | 5284 (http), 7176 (https) | ASP.NET Core | none | - | `/swagger` (Development) |
| chatbot_service | 8000 | FastAPI | NVIDIA NIM | yes | `GET :8000/health` |
| GymAgentService | 8001 | FastAPI + LangGraph | NVIDIA NIM or OpenRouter | yes | `GET :8001/health` |
| FitnessAgentService | 8002 | FastAPI + LangGraph | OpenRouter | yes | `GET :8002/health` |
| DietPlanService | 8003 | FastAPI (custom coordinator) | NVIDIA NIM | yes | `GET :8003/health` |
| TimeManagementAgentService | 8004 | FastAPI + LangGraph | OpenRouter | yes | `GET :8004/health` |
| Web app (Vite) | 5173 | React | - | no (`npm run dev`) | open in browser |

At a glance, how the agents differ:

| | Diet | Fitness | Gym | Time |
|---|---|---|---|---|
| Service-level auth | JWT re-checked + optional service key | service key | service key (fails closed) | none (loopback only) |
| Human approval | Trainer/Admin approve **high-risk** plans (enforced in the service) | none (a profile flag pauses planning) | Gym_Owner/Admin approve **every** run (LangGraph `interrupt()`) | Gym_Owner/Admin approve **every** generated timetable (enforced in the .NET API, see below) |
| Prompt-injection guard | yes | prompt wording only | yes | yes (pattern-based) |
| Python tests | yes (CI) | yes (CI job is advisory: 12 of 22 tests fail today) | yes (CI) | yes (CI, offline) |

---

## Project Structure

```
VitroFit/
├── BackendAPI/
│   ├── .env.example              # THE environment template (copy to .env)
│   ├── requirements.txt          # THE Python requirements for every service + tests
│   ├── venv/                     # THE shared Python virtual environment (git-ignored, you create it)
│   ├── VitroFit.API/             # ASP.NET Core Web API
│   │   ├── Controllers/          # Auth, Admin, Timetable, Workouts
│   │   ├── Features/             # AdaptiveFitness, DietAgent, GymAgent, GymOwners, TimetableVerification
│   │   ├── Data/ Entities/ Dtos/ Migrations/ Services/ Settings/
│   │   ├── Program.cs            # startup, DI, JWT, CORS, rate limits, Python sidecar auto-start
│   │   └── appsettings.json      # non-secret configuration
│   ├── VitroFit.API.Tests/       # xUnit tests (Diet + Gym gateways, gym validator, timetable verification)
│   ├── FitnessAgent.Tests/       # console regression checks for the fitness rules
│   ├── GymAgentService/          # port 8001
│   ├── FitnessAgentService/      # port 8002
│   ├── DietPlanService/          # port 8003
│   ├── TimeManagementAgentService/ # port 8004
│   └── chatbot_service/          # port 8000
├── VitroFit_web/                 # React (Vite) web app (its own small .env for 3 VITE_ URLs)
├── vitrofit_mobile/              # Flutter mobile app
├── docs/                         # ADRs, evaluation and performance reports, technical documents
└── README.md                     # this file
```

---

## Prerequisites

| Tool | Version | Check with |
| ---- | ------- | ---------- |
| .NET SDK | 10.0+ | `dotnet --version` |
| Node.js | 20+ (LTS) | `node --version` |
| PostgreSQL | 13+ | running on port 5432 |
| Python | 3.12 | `python --version` |
| Flutter (mobile only) | stable, Dart 3.12+ | `flutter --version` |

---

## Quick Start (first run)

1. **Create the database.** Start PostgreSQL and create an empty database named `VitroFit`. The API creates and migrates the tables itself on start-up.

2. **Create the one environment file.**

   ```bash
   cd BackendAPI
   cp .env.example .env          # Windows: copy .env.example .env
   ```

   Fill in at least the database strings, `JwtSettings__Secret`, and the service keys. See [Configuration](#configuration) for what each group is for. It is git-ignored; never commit it.

3. **Create the one Python environment** (needed by all five Python services):

   ```bash
   cd BackendAPI
   python -m venv venv
   venv\Scripts\pip install -r requirements.txt        # Windows
   venv/bin/pip install -r requirements.txt            # macOS / Linux
   ```

   The first install is large (about 1.5 GB) because the Gym agent uses PyTorch and ChromaDB.

4. **Start the backend** (this also starts all five Python services from `BackendAPI/venv`):

   ```bash
   cd BackendAPI/VitroFit.API
   dotnet run
   ```

   - API: `http://localhost:5284`, Swagger: `http://localhost:5284/swagger`
   - Each service logs "Started ... sidecar" in the API console. If you see "shared Python venv not found", redo step 3.

5. **Start the web app:**

   ```bash
   cd VitroFit_web
   npm install
   npm run dev                  # http://localhost:5173
   ```

   Web settings live in `VitroFit_web/.env` (copy `.env.example`): `VITE_API_BASE_URL` (default `http://localhost:5284/api`), `VITE_CHATBOT_API_URL` (default `http://localhost:8000/api/chat`), `VITE_DIET_AGENT_API_URL` (default `http://localhost:5284/api/diet`). Vite only reads variables from its own folder, so these three stay in the web project. Restart `npm run dev` after editing it.

6. **Sign in** with the [default admin](#default-admin-account), or register a new account (email OTP required).

7. **Mobile (optional):** see [Mobile App](#mobile-app).

For basic local development you only need the database connection string and a JWT secret. SMTP, Cloudinary and the agents' keys are needed only for their own features (email OTPs, profile photos, Find Gyms, Chatbot, Diet, Fitness, Time).

---

## Configuration

### One environment file: `BackendAPI/.env`

Every backend setting and secret (the .NET API and all five Python services) lives in `BackendAPI/.env`, created from `BackendAPI/.env.example`. The template lists every variable, grouped by service, with the defaults.

- The .NET API loads it at start-up (DotNetEnv). A double underscore maps to a colon in `appsettings.json`: `JwtSettings__Secret` means `JwtSettings:Secret`.
- The API passes its environment on to the Python services it starts, so the values in this file always win. The Python services also locate this file by themselves when you run them by hand.
- There are no per-service `.env` files. If an old one is lying around in a service folder, delete it: when you run that service by hand it would override the shared values.
- `appsettings.json` only holds non-secret settings (issuer, audience, token lifetimes, service base URLs, SMTP host/user, Cloudinary cloud name). Secret fields there are empty on purpose.

| Group | Variables | Notes |
| ----- | --------- | ----- |
| Database | `ConnectionStrings__DefaultConnection` (.NET), `DATABASE_URL` (Gym, Diet; SQLAlchemy `postgresql+psycopg2://...`), `FITNESS_DATABASE_URL` (Fitness, Time; `postgresql://...`) | All three point at the same `VitroFit` database. |
| Auth and email | `JwtSettings__Secret` (32+ random characters), `EmailSettings__Password` (Gmail App Password), `Cloudinary__ApiKey`, `Cloudinary__ApiSecret` | The Diet service reads the same JWT secret to re-verify tokens. |
| Service keys | `GYM_AGENT_KEY` = `GymAgent__ServiceKey`; `FITNESS_SERVICE_KEY` = `FitnessAgent__ServiceKey`; optional `DIET_AGENT_KEY` = `DietAgent__ServiceKey` | Each pair must be identical, 32+ characters. A too-short key makes the API refuse to call that service (503). The Time service has no key. |
| LLM | `NVIDIA_API_KEY`, `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` | Get keys at [build.nvidia.com](https://build.nvidia.com/) and [openrouter.ai](https://openrouter.ai/). |
| Per service | see the template | Chatbot `NVIDIA_MODEL_PRIMARY/FALLBACK`; Diet `DIET_*`; Gym `LLM_PROVIDER`, `NVIDIA_MODEL`, `TAVILY_API_KEY`, `GOOGLE_PLACES_API_KEY`, `AGENT_*`, `GYM_*`; Fitness `FITNESS_API_URL`; Time `TIME_MANAGEMENT_PORT` |

Other `appsettings.json` blocks you may change: `EmailSettings` (Gmail: host `smtp.gmail.com`, port 587, `UseSsl` false, your username and sender), `JwtSettings` (issuer `VitroFitApi`, audience `VitroFitWeb`, 60-minute access tokens, 30-day refresh tokens), and the agent base URLs (`DietAgent`, `GymAgent`, `FitnessAgent`, `TimeManagementAgent`).

### Database and migrations

The API applies pending EF Core migrations for both the main context and the fitness context (`fitness` schema, own history table) on every start, and seeds the admin account. To apply them without starting the API: `dotnet ef database update` (add `--context FitnessDbContext` for the fitness schema). Never run migrations against a shared or deployed database without review.

---

## Running the Python Services

`VitroFit.API` starts all five services automatically on `dotnet run` and stops them on shutdown. For each one it checks that the port is free and that `BackendAPI/venv` exists, then runs the command below with the service's own folder as the working directory. If the venv is missing, that service is skipped with a warning and the API still starts.

To run one by hand (for example to read its logs), use the shared venv from the service's folder:

| Service | Command (from its folder in `BackendAPI/`) |
| ------- | ------------------------------------------ |
| GymAgentService | `..\venv\Scripts\python server.py` |
| FitnessAgentService | `..\venv\Scripts\python -m app.server` |
| DietPlanService | `..\venv\Scripts\python -m uvicorn main:app --port 8003` |
| TimeManagementAgentService | `..\venv\Scripts\python -m app.server` |
| chatbot_service | `..\venv\Scripts\python -m uvicorn main:app --port 8000` |

(macOS / Linux: `../venv/bin/python`.) Gym, Fitness and Time use `server.py` / `-m app.server` because the PostgreSQL checkpointer needs a selector event loop on Windows. Stop the copy the API started first (or stop the API), otherwise the port is busy.

---

## The AI Agents

### Diet Plan agent (port 8003)

Turns a user's profile into a one-day meal plan. Browsers call it through the API (`/api/diet/*`), which passes each request on with the caller's token and the shared key.

```
planner -> NutritionAnalystAgent -> MealGeneratorAgent -> SafetyValidatorAgent
validator: pass            -> done (low/medium risk: auto_approved, high risk: pending review)
           revise (max 1)  -> back to MealGeneratorAgent with the violations as feedback
           reject          -> rejected (nothing can be saved)
           retries used up -> closest plan marked "outside tolerance" (a reject-tier problem is never returned)
```

`POST /api/diet/generate` answers at once with a `workflowId`; the run continues in the background and the clients poll `GET /api/diet/workflows/{id}`. `POST .../refine` applies one free-text edit.

| Agent | Tools | LLM |
|---|---|---|
| planner | none | no |
| NutritionAnalystAgent | `calculate_targets`, `assess_risk`, `lookup_budget` | no |
| MealGeneratorAgent | `generate_meals`, `refine_meals` | yes |
| SafetyValidatorAgent | `validate_plan` | no |

Only the meal generator uses the LLM. Calories and macros come from `src/tools/calculator.py` (Mifflin-St Jeor), so the numbers are reproducible and the model can only choose foods. Every tool call goes through `workflow.call_tool` (role allow-list, plan narrowing, Pydantic contract, timeout, trace event). The total run budget is 230 s.

**Approval.** The analyst assigns `low`, `medium` or `high` risk from age, medical conditions and calorie deficit. Only high risk needs a human: the run ends `completed` with `approvalStatus: "pending"`; `POST /confirm` and `PUT /plans/{id}` answer 409 until a Trainer or Admin approves; a rejected plan can never be saved; a decision is a single conditional `UPDATE`, so two reviewers cannot both win; the approver's id, role, note and time are stored; editing an approved high-risk plan sends it back to `pending`.

**Validator rules** (deterministic, `src/utils/validators.py`): schema; calories within 10% (revise) or 50% (reject); macro plausibility; 1 to 8 meals; restriction violations reject (vegetarian, vegan, halal, dairy-free, lactose-intolerant, gluten-free, peanut allergy); dislikes revise; below the safe calorie floor rejects; diabetes sugar, sodium and fried-fat checks revise; links, markup or injection text in output is revised once, then rejected.

**Prompt-injection guard** (`src/utils/injection_guard.py`, no LLM): normalises text (NFKC, invisible characters removed, look-alike letters folded), refuses strong instruction-like signals in `dislikes` and the refine instruction with 422, escapes angle brackets in prompts, and checks model output. `DIET_INJECTION_MODE=monitor` records without refusing.

**State** (PostgreSQL): `diet_plan_inputs`, `diet_plans`, `diet_workflows` (check constraints on `status`, `approval_status`, `risk_level`), `diet_workflow_steps` (unique `(workflow_id, seq)`). A step row is written in the same transaction as the workflow update. On start-up, interrupted runs are finished off. At most `DIET_MAX_CONCURRENT_WORKFLOWS` (default 3) runs use the LLM at once.

**Internal-only mode.** Set `DIET_AGENT_KEY` and `DietAgent__ServiceKey` to the same 32+ character value and every `/api/diet` route also needs `X-Diet-Agent-Key`, so only the API can call the service. The caller's JWT is still verified in Python for identity, ownership and roles. The API side (`Features/DietAgent`) adds JWT, a per-user rate limit on `generate` and `refine` (20 per minute), a path allow-list, a 512 KB body limit and a pass-through of the service's status and body. Logs: one line per event with the workflow id; prompts and model replies are never logged (`DIET_LOG_LEVEL`).

Layout: `main.py`, `src/agent/` (workflow, runner, store, `nodes/`), `src/api/` (app, routes), `src/models/`, `src/prompts/`, `src/tools/`, `src/utils/`, `tests/`.

### Fitness / Workout agent (port 8002)

A Python FastAPI/LangGraph service proposes beginner workout schedules. Browsers never call it; the API does (`/api/fitness/*`). After the four beginner schedules the agent works in progressive blocks of 3 or 4 workout days. The three-month cycle is an analysis period, not a generated 90-day calendar. Every block day has exercises (no rest-only days), sessions run about 100 to 120 minutes, and members record performance, effort, pain and affected areas before the next block. Pain records adapt affected exercises while keeping suitable workouts for other areas; significant, worsening or persistent pain should prompt qualified professional guidance. The feature is for adult beginners and is not medical clearance.

Graph: `coordinator -> screening -> progress_analyst -> planner -> validator` (up to 3 planner attempts). Screening stops the run (`ReviewRequired`) if the profile flags a health concern. The service re-builds the plan from preset tables and rules (`rules.py`), the .NET side re-validates it (`FitnessPolicy`), and a failed first workflow can be replaced up to twice while the failed history stays saved.

Setup specifics: set `FITNESS_SERVICE_KEY` (= `FitnessAgent__ServiceKey`), `FITNESS_API_URL` (API base, e.g. `http://127.0.0.1:5284`, no `/api`), `FITNESS_DATABASE_URL`, `OPENROUTER_API_KEY` and `OPENROUTER_MODEL` in `BackendAPI/.env`. Fitness tables live in the `fitness` schema of the same database and migrate automatically on API start.

State: the API owns profiles, the exercise catalog (45 seeded exercises), workflows, plan versions, progress and audit events; Python owns orchestration and the LangGraph checkpoint tables. Tests: `pytest` (see [Tests and CI](#tests-and-ci)) and `dotnet run --project BackendAPI/FitnessAgent.Tests`. If fitness requests return 503: check the agent and API are running, the keys match, and `FitnessAgent:BaseUrl` points to port 8002. A 401 from the agent means the keys differ; provider 401/403 is a bad OpenRouter key or model permission, 402 is no credits, 429 is rate limiting.

### Gym Finding agent (port 8001)

Internal FastAPI + LangGraph service. **Only the API calls it**; clients use `/api/gyms/*` and `/api/gym-agent/workflows/*`, where JWT and roles are enforced.

- Every route except `/health` needs the `X-Gym-Agent-Key` header (32+ characters, constant-time compare); with no key configured every request gets 503. It binds to 127.0.0.1 only, accepts only `127.0.0.1`/`localhost` Host headers (`GYM_ALLOWED_HOSTS`), has no CORS and no `/docs`.
- The API adds JWT, roles, per-user rate limits and timeouts (AI calls 150 s, others 30 s).

Objective: collect verified equipment, classes and contact details for a gym and recommend four workouts, then publish as `verified` only after a Gym_Owner or Admin approves.

```
planner -> gym_analysis -> workout_recommendation -> validator
validator: pass -> approval_gate (interrupt) -> publish
           revise (max 2) -> back to the agent named in the violation
           reject / exhausted -> safe_fail
approval_gate: approve -> publish | reject -> end | revise (max 2) -> workout_recommendation
```

| Agent | Tools | LLM |
|---|---|---|
| planner | none | no |
| gym_analysis | `scrape_gym_website`, `search_gym_info`, `lookup_similar_gyms` (narrowed by the plan) | yes |
| workout_recommendation | `list_equipment_taxonomy` (offline, read-only) | yes |
| validator | none | no |

Every tool call goes through `call_tool`: role allow-list, plan narrowing, input schema, scraping only the gym's own public host, timeout, sanitised output. Contact details must be backed by a snippet found in the retrieved text. State is in PostgreSQL: the LangGraph checkpointer (so a paused approval survives restarts) plus `gym_agent_workflows` (with approval fields), `gym_agent_steps` and `gym_agent_tool_calls`; a node's step, tool calls and workflow update are written in one transaction.

**How data becomes `verified`** (four independent layers): (1) the graph pauses at `approval_gate` with `interrupt()`; (2) `store.publish` is the only code that writes `source='verified'` and refuses unless the row records an approval by an approver role; (3) the database check `source <> 'verified' OR verified_workflow_id IS NOT NULL` refuses a verified row without an approving workflow; (4) `/internal/gyms/details` can only write `ai-*` sources. Reviewers use the web page `/admin/gym-approvals` (Admin and Gym_Owner).

**Prompt-injection guard** (`src/utils/injection_guard.py`): applied to tool output (a strong source is withheld entirely), model-chosen tool arguments, request fields, prompt fences and model output. Codes are stored on the tool call, never the text. `GYM_INJECTION_MODE=monitor` records without changing anything; `GYM_INJECTION_BLOCK_SCORE` tunes the threshold.

**Validator rules** (deterministic, `src/utils/validators.py` and `src/tools/url_policy.py`): `reject` severities stop the run (`REQUEST_WEBSITE_INVALID`, `NO_USABLE_DATA`); `revise` sends violations back to the named agent (max 2). Groups: URL allow-list, evidence and contacts (needs a retrieved snippet, confidence at least 0.6), business rules, workouts and safety (exactly 4, 10 to 120 minutes, listed equipment only, no medical claims, beginners at most 60 minutes). A source URL only counts if it is public https, on the gym's own site or in `GYM_URL_ALLOWLIST` (matched on a domain boundary), and was actually retrieved in this run.

Logging: one line per event with workflow id and node, never prompts, replies or secrets (`GYM_LOG_LEVEL`).

Layout: `main.py` (entry point; `server.py` is a shim), `src/agent/` (graph, runner, store, checkpointer, `nodes/`, `legacy/`), `src/tools/`, `src/models/`, `src/prompts/`, `src/utils/`, `src/api/`, `tests/`, `perf/`. `/internal/gyms/details` and `/internal/gyms/workouts` are the older single-agent enrichment used by Find Gyms; they can only write `ai-*` data. Mobile and web "nearby" search goes `POST /api/gyms/nearby` to the Google Places key (`GOOGLE_PLACES_API_KEY`) held by this service.

Gym owners register on the web (`/register-gym`, multipart); an Admin approves or rejects applications on the admin dashboard, and an owner cannot log in until approved.

**Latency measurements** (`perf/measure_latency.py`, writes `reports/perf/latest.json` and `latest.md`, git-ignored). Run from `BackendAPI/GymAgentService` against a scratch database:

```bash
python -m perf.measure_latency --database-url postgresql+psycopg2://user:pw@localhost:5432/gym_perf
python -m perf.measure_latency --database-url ... --quick              # about 10x fewer iterations
python -m perf.measure_latency --sections components,stored            # no database needed
```

Sections: `components` (guard, validator, URL policy, planner), `database` (store round trips), `workflows` (whole workflows at concurrency 1, 5, 10, 25), `http` (internal API at 1, 10, 50) and `stored` (real LLM timings read from earlier runs). `--live` with `GYM_PERF_ALLOW_LIVE=1` runs real workflows and uses API quota.

### Time Management agent (port 8004) and timetable verification

**Agent.** `POST /internal/generate_timetable` turns a Ready fitness plan and profile into a week of timed sessions plus a short long-term-impact note. LangGraph: `coordinate -> schedule -> analyze -> validate` (up to 3 attempts). It uses OpenRouter and `FITNESS_DATABASE_URL` for its checkpointer. It listens on `127.0.0.1:8004` (`TIME_MANAGEMENT_PORT`), has no key of its own; a prompt-injection guard (`app/injection_guard.py`, `TIME_INJECTION_MODE=enforce|monitor`, `TIME_INJECTION_BLOCK_SCORE`) refuses a hostile `preferences` note with a `Failed` result before any model call and rejects slot or impact text that carries instructions, links or markup; the API reaches it at `TimeManagementAgent:BaseUrl`.

**Human verification (enforced in the API, not in the agent).** A generated timetable is never applied directly:

1. A member calls `POST /api/fitness/workflows/{id}/timetable?preferences=` (needs a Ready workflow and a profile). The API gets the timetable from the agent and stores it as a **proposal** with status `Pending`; older pending proposals become `Superseded`. The reply is `{status: "PendingVerification", proposalId, longTermImpact, slotCount, message}`.
2. Every eligible reviewer gets an in-app notification (`timetable.review-requested`): email-verified Admins, plus Gym_Owners who are approved (or have no application). The requester is never notified.
3. Reviewers (Gym_Owner, Admin) open the review queue (web page `/timetable-reviews`), see the proposal without the member's email, phone, age or weight, and approve, or reject with a required note (max 500 characters). A reviewer cannot review their own request, except that an Admin may approve their own.
4. The decision is claimed with one conditional update (`WHERE Status = Pending`), so only one reviewer wins (409 for a second decision).
5. On approval the member's existing slots are replaced with the proposal's slots in one transaction (unknown workout names become "Adaptive" workouts). The member is notified in-app and by email; an email failure only logs a warning.
6. The member can withdraw a pending request (`POST /api/timetable/proposal/{id}/cancel`).

Statuses: `Pending`, `Approved`, `Rejected`, `Cancelled`, `Superseded`. Tables: `TimetableProposals` (jsonb slots, equipment array, reviewer, timestamps) and `UserNotifications`. The web Timetable page shows pending, verified and rejected panels with a cancel button (polls every 30 s) and the navbar has a notification bell. The mobile app does not have the proposal, review or bell screens yet.

Plain timetable editing (without AI) is unchanged: `GET/POST/PUT/DELETE /api/timetable`, and the workout catalog `/api/workouts` (Admin edits).

### Chatbot (port 8000)

FastAPI + NVIDIA NIM, streams `text/event-stream` replies from `POST /api/chat`. Settings: `NVIDIA_API_KEY`, `NVIDIA_MODEL_PRIMARY`, `NVIDIA_MODEL_FALLBACK`. No login is needed; both clients call it directly (CORS is enabled).

---

## Mobile App

`vitrofit_mobile` mirrors the web app against the same API (`/api`, JWT). Six bottom tabs:

| Tab | What it does | Backend |
| --- | --- | ------- |
| Home | Overview and shortcuts | `/api/timetable` (next session) |
| Fitness | Fitness agent: profile, plans, progress, 3-month blocks | `/api/fitness/*` |
| Gym | Nearby gyms (Google Maps), details, workout suggestions | `/api/gyms/*` |
| Diet | AI meal plans, refine, save; Trainer/Admin approvals queue | `/api/diet/*` |
| Time | AI timetable from a Ready fitness plan, editable by hand | `/api/fitness/workflows/{id}/timetable`, `/api/timetable` |
| Profile | Account and settings | `/api/auth/*` |

The app never calls the agents directly (except the chatbot), so only the API base URL has to change for a deployed backend. It is set at build/run time:

```bash
cd vitrofit_mobile
flutter pub get
flutter run                                                           # Android emulator: first run `adb reverse tcp:5284 tcp:5284`
flutter run --dart-define=API_BASE_URL=http://192.168.1.20:5284/api   # physical device on the same Wi-Fi
flutter build apk --dart-define=API_BASE_URL=https://your-api.example.com/api
```

The chatbot URL is `--dart-define=CHATBOT_API_URL=...` (default `http://127.0.0.1:8000`). Tokens are kept in secure storage and refreshed automatically once on a 401.

**Google Maps (Gym tab).** In Google Cloud enable *Maps SDK for Android* and *Places API (New)* (billing on). Create a native key restricted to the Android app (`com.example.vitrofit_mobile` + your SHA-1) and put it in `vitrofit_mobile/android/local.properties` (git-ignored) as `MAPS_API_KEY=...`. Place search needs no key in the app: it calls `POST /api/gyms/nearby`, which uses `GOOGLE_PLACES_API_KEY` from `BackendAPI/.env` (restrict that key to Places API (New)). Restart the API after changing it.

Known limits: the Time tab does not yet show timetable verification (see above), there are no push notifications, and iOS still needs a location usage string in `Info.plist`.

---

## API Endpoints

All routes are under `/api`. 🔒 = needs `Authorization: Bearer <access token>`.

### Auth: `/api/auth`

| Method | Route | Auth | Description |
| ------ | ----- | ---- | ----------- |
| POST | `/auth/register` | - | Create account, sends a 6-digit email-verification OTP |
| POST | `/auth/register-gym-owner` | - | Multipart gym-owner application (rate limited, 60 MB cap) |
| POST | `/auth/login` | - | Email + password, returns access + refresh tokens (403 `GYM_PENDING` / `GYM_REJECTED` for unapproved owners) |
| POST | `/auth/verify-email` | - | Validate the OTP, activate the account, return tokens |
| POST | `/auth/resend-verification` | - | Re-send the OTP |
| POST | `/auth/refresh` | - | Exchange a refresh token for a new pair |
| GET | `/auth/me` | 🔒 | Current profile |
| POST | `/auth/me/photo` | 🔒 | Upload a profile photo (multipart `file`) |
| POST | `/auth/change-password` | 🔒 | Change password |
| DELETE | `/auth/me` | 🔒 | Delete the account |
| POST | `/auth/forgot-password`, `/auth/reset-password` | - | Reset password with an emailed OTP |

### Admin: `/api/admin` (Admin role)

| Method | Route | Description |
| ------ | ----- | ----------- |
| GET / POST | `/admin/users` | List users (`?role=`) / create a verified user |
| DELETE | `/admin/users/{id}` | Delete a user (not yourself) |
| GET | `/admin/gym-applications[?status=]`, `/admin/gym-applications/{id}` | Gym-owner applications |
| POST | `/admin/gym-applications/{id}/approve`, `/reject` | Decide (reject needs a note) |

### Timetable, workouts, verification, notifications

| Method | Route | Auth | Description |
| ------ | ----- | ---- | ----------- |
| GET / POST | `/timetable` | 🔒 | Own slots / create a slot |
| PUT / DELETE | `/timetable/{id}` | 🔒 | Update / delete own slot |
| GET | `/workouts` | 🔒 | Workout catalog |
| POST / PUT / DELETE | `/workouts[/{id}]` | Admin | Manage the catalog |
| POST | `/fitness/workflows/{id}/timetable?preferences=` | 🔒 | Generate a timetable proposal (`PendingVerification`) |
| GET | `/timetable/proposal` | 🔒 | Latest proposal of the caller |
| POST | `/timetable/proposal/{id}/cancel` | 🔒 | Withdraw a pending proposal |
| GET | `/timetable-reviews?status=` | Gym_Owner, Admin | Review queue (Pending, Approved, Rejected) |
| GET | `/timetable-reviews/{id}` | Gym_Owner, Admin | Proposal detail |
| POST | `/timetable-reviews/{id}/approve`, `/reject` | Gym_Owner, Admin | Decide (reject needs a note) |
| GET | `/notifications` | 🔒 | The caller's notifications |
| POST | `/notifications/{id}/read`, `/notifications/read-all` | 🔒 | Mark as read |

### Fitness: `/api/fitness` (🔒)

| Method | Route | Purpose |
|---|---|---|
| GET / PUT / DELETE | `/fitness/profile` | Read, save, delete the caller's profile |
| GET | `/fitness/exercises` | Exercise catalog |
| POST | `/fitness/workflows` | Start the first schedule, or the next block from recorded progress |
| GET | `/fitness/workflows?page=1&status=` | Paged schedules |
| GET | `/fitness/workflows/{id}`, `/history` | One schedule, audit and progress history |
| POST | `/fitness/workflows/{id}/retry`, `/regenerate` | Retry a failed run / regenerate (clears progress) |
| PUT | `/fitness/workflows/{id}/progress` | Record workout, effort, pain, affected areas |
| GET / POST | `/fitness/workflows/{id}/next-cycle` | Read / save the three-month review |

### Diet: `/api/diet` (🔒, passed through to the Diet service)

| Method | Route | Description |
| ------ | ----- | ----------- |
| POST | `/diet/generate` | Start a plan; returns a `workflowId` at once |
| GET | `/diet/workflows/{id}`, `/trace` | Live progress and result / full audit trace |
| POST | `/diet/workflows/{id}/refine` | Free-text edit of a generated plan |
| POST | `/diet/confirm` | Save a generated plan |
| GET | `/diet/plans` | Saved plans |
| PUT / DELETE | `/diet/plans/{id}` | Update / delete a saved plan |
| GET | `/diet/approvals/pending` | High-risk plans awaiting review (Trainer/Admin) |
| POST | `/diet/workflows/{id}/approve`, `/reject?note=` | Decide (Trainer/Admin) |

### Gyms: `/api/gyms` and `/api/gym-agent/workflows` (🔒)

| Method | Route | Description |
| ------ | ----- | ----------- |
| POST | `/gyms/nearby` | Nearby gyms (Google Places via the Gym service) |
| GET | `/gyms/maps-config` | Maps key for the web map |
| POST | `/gyms/details`, `/gyms/workouts` | AI enrichment / 4 workout suggestions |
| POST | `/gym-agent/workflows` | Start a verification run (Gym_Owner, Admin) |
| GET | `/gym-agent/workflows`, `/pending`, `/{id}`, `/{id}/events` | List and inspect runs |
| POST | `/gym-agent/workflows/{id}/approve`, `/reject`, `/revise` | Human decision (Gym_Owner, Admin) |

### Python services (internal)

Gym: `/internal/gyms/{details,workouts,nearby,maps-config}` and `/internal/workflows/...` with `X-Gym-Agent-Key`. Fitness: `POST /internal/generate`. Time: `POST /internal/generate_timetable`. Chatbot: `POST /api/chat`. All have `GET /health`.

---

## Tests and CI

Use the shared venv for every Python test run (no separate install): `venv\Scripts\python -m pytest ...` from the service folder.

| Suite | Command (from) | Notes |
| ----- | -------------- | ----- |
| .NET API | `dotnet test BackendAPI/VitroFit.API.Tests` | Diet and Gym gateways, gym-application validator, timetable verification |
| Diet service | `pytest` (`BackendAPI/DietPlanService`) | SQLite with an 80% coverage gate; `TEST_DATABASE_URL=postgresql+psycopg2://user:pw@localhost:5432/diet_test pytest` for real PostgreSQL; `pytest -m evaluation` (20 golden cases); `pytest -m perf`; `python tests/evaluation/mutation_check.py` |
| Gym service | `pytest` (`BackendAPI/GymAgentService`) | Everything except timing tests, on SQLite; `TEST_DATABASE_URL=...` for PostgreSQL; `pytest --cov` (80% gate); `pytest -m evaluation` (21 golden cases); `pytest -m perf` |
| Time service | `pytest` (`BackendAPI/TimeManagementAgentService`) | ~120 offline tests (injection guard, workflow, LLM client, schemas, API), 80% coverage gate |
| Fitness service | `pytest` (`BackendAPI/FitnessAgentService`) | 22 tests, no network. 12 currently fail (they predate the current planner rules and need updating) |
| Fitness rules (.NET) | `dotnet run --project BackendAPI/FitnessAgent.Tests` | Console regression checks |
| React | `npm run lint`, `npm run build` (`VitroFit_web`) | No unit tests yet |
| Flutter | `flutter analyze --no-fatal-infos`, `flutter test` (`vitrofit_mobile`) | Model and smoke tests |

No Python test needs the network, an API key or a real model: models and tools are scripted, and `tests/conftest.py` makes any attempt to reach a real LLM fail loudly. Tests never touch your development database. The chatbot has no automated tests.

CI (`.github/workflows/ci.yml`) runs on every push and pull request to `main` and `development`: `dotnet` (build and test), `gym-agent-service` and `diet-plan-service` (pytest on SQLite and PostgreSQL 17, evaluation, latency smoke tests), `time-management-service` (offline pytest with an 80% coverage gate), `web` (lint, build), `flutter` (analyze, test) and a `ci-success` gate. The Python jobs install CPU-only PyTorch first, then `BackendAPI/requirements.txt`. There is also a `fitness-agent-service` job (offline pytest) that is **advisory only**: it is marked `continue-on-error` and is not in the gate, because 12 of its tests fail today. Once they are fixed, remove `continue-on-error` and add the job to `ci-success.needs`. The chatbot has no tests and the `FitnessAgent.Tests` console project is not in CI.

---

## Default Admin Account

Seeded automatically on backend start-up:

| Field | Value |
| ----- | ----- |
| Email | `admin@gmail.com` |
| Password | `admin1234` |

Email-verified, `Admin` role; sign in at `/login`, admin dashboard at `/admin`. Change these credentials before any real deployment.

---

## Troubleshooting

**Web app can't reach the API.** Confirm the backend is running and `VITE_API_BASE_URL` matches its port (default `http://localhost:5284/api`). Restart the Vite dev server after editing `.env`.

**Login says "Please verify your email".** New accounts must verify with the emailed OTP first. No email arrives: check spam and that `EmailSettings` has a valid SMTP/App password.

**Database errors, connection refused.** Make sure PostgreSQL is running on port 5432 and the credentials in `ConnectionStrings__DefaultConnection` are right. Tables are created and migrated automatically on API start.

**"shared Python venv not found" in the API log.** The services were skipped. Do step 3 of the Quick Start in `BackendAPI`, then restart the API.

**A feature returns 503 or "connection refused" on port 800x.** That service is not running. Check the API log for its start-up lines, call `GET http://127.0.0.1:<port>/health`, and run it by hand ([Running the Python Services](#running-the-python-services)) to see its logs. For the Time agent also check `FITNESS_DATABASE_URL` and `OPENROUTER_API_KEY`, and that the user has a fitness plan with status Ready.

**Port already in use.** API 5284 (7176 https), Vite 5173, chatbot 8000, Gym 8001, Fitness 8002, Diet 8003, Time 8004 (`TIME_MANAGEMENT_PORT`). A service already listening on its port is not started again; stop the old copy (`netstat -ano | findstr :8004`, then `taskkill /PID <pid> /F`) or change the port.

**A service uses the wrong keys when run by hand.** Delete any stray `.env` file in a service folder. Only `BackendAPI/.env` is read.

**Fitness / Gym 401 from the agent.** The service key pair does not match (`FITNESS_SERVICE_KEY` and `FitnessAgent__ServiceKey`, or `GYM_AGENT_KEY` and `GymAgent__ServiceKey`), or is shorter than 32 characters.

**Chatbot answers with an error.** `NVIDIA_API_KEY` is missing or invalid in `BackendAPI/.env`.

---

## Other Documentation

`docs/adr/` holds the architecture decision records (Gym agent 0001 and 0002, Diet agent 0003), `docs/evaluation/` the agent evaluation reports, `docs/performance/` the Gym latency report, and `docs/` the technical documents.
