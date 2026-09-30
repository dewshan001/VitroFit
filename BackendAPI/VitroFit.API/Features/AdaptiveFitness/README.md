# Adaptive Fitness Feature

This feature adds an internal Python LangGraph workflow, public ASP.NET Core endpoints, a React member screen, and a Flutter member screen. Client apps call ASP.NET only. The Python service binds locally and accepts requests only with a shared service key.

## Local setup

1. Copy `BackendAPI/FitnessAgentService/.env.example` to `.env` in that folder. Set `FITNESS_DATABASE_URL` to the same **local VitroFit PostgreSQL database** used by ASP.NET, plus an OpenRouter API key, a model ID, and a random `FITNESS_SERVICE_KEY` of at least 32 characters. Set `FITNESS_API_URL` to the ASP.NET API base address. Do not commit `.env`.
2. Configure the matching `FitnessAgent:ServiceKey` and `FitnessAgent:BaseUrl` using .NET user secrets or environment variables. Example PowerShell commands from `BackendAPI/VitroFit.API`:

   ```powershell
   dotnet user-secrets set 'FitnessAgent:ServiceKey' '<same-random-key>'
   dotnet user-secrets set 'FitnessAgent:BaseUrl' 'http://127.0.0.1:8002'
   ```

3. From `BackendAPI/FitnessAgentService`, create a Python virtual environment and install `requirements.txt`. When started from `BackendAPI/VitroFit.API`, the backend starts the agent as a child process with `python -m app.server` if port `8002` is free, and stops that child when the API shuts down. The runner selects the Windows event loop required by psycopg's async PostgreSQL driver. To run the agent manually for debugging, start it from `BackendAPI/FitnessAgentService` with `python -m app.server`.
4. Apply the feature migration explicitly to your local database:

   ```powershell
   dotnet ef database update --context FitnessDbContext --configuration Debug
   ```

   The migration creates the `fitness` schema and its own migration-history table in the configured database. It is not applied automatically at API startup. Verify the connection string targets your local database before applying. Never run this command against a shared/deployed database without team review.

5. Start the existing web app and mobile app. Web route: `/adaptive-fitness`. Flutter entry: the sparkle button in the main app bar. For an Android emulator, use `--dart-define=FITNESS_API_BASE_URL=http://10.0.2.2:5284/api`; for a physical phone, set the machine's reachable LAN URL. The fitness sign-in uses the existing verified VitroFit account and stores its access token in Flutter secure storage.

## Workflow and safety

The member completes the existing four beginner schedules, then reviews pain or discomfort, injuries or restrictions, current condition, goal, workout time, and available equipment. The three-month period is an analysis window, not a prebuilt calendar. The agent generates only the next 3 or 4 workout days; every generated day contains exercises and is labeled Day 01, Day 02, and so on. It does not generate rest-only or recovery-only entries. Each session is about 100–120 minutes, based on available workout time. The user records completion, effort, date, and any affected body area for every workout before requesting another block. Pain does not stop the whole program: the agent avoids exercises targeting reported areas, continues suitable workouts for other areas, and stores original exercise, replacement, and reason. Significant, worsening, or persistent pain calls for qualified professional guidance. A declared profile health concern still pauses self-scheduling. At the end of three months, the app analyzes the period and asks the user to review the same condition and training questions before starting another period. Repeated generation from an earlier block is rejected. Invalid plans get at most three planner attempts. A failed first workflow may be replaced with up to two fresh attempts while the failed history remains saved. The Python model cannot approve plans or call arbitrary tools. The Python LangGraph checkpoint tables and ASP.NET feature tables share the existing PostgreSQL database; checkpoint state is keyed by run ID. No chain-of-thought is stored.

The profile asks about exercise-related symptoms, conditions needing clearance, recent surgery or injury, pregnancy-related restrictions, and clinician advice. A flagged answer pauses self-scheduling; it is not a diagnosis or medical clearance. Seed exercises and equipment labels are a curated starter catalog, not verified data from the AI-enriched gym service. A human must confirm gym equipment. Body image is not collected or assessed.

## API

All member calls go through the ASP.NET API with the existing JWT:

| Method | Route | Purpose |
|---|---|---|
| GET/PUT | `/api/fitness/profile` | Read and save caller's profile |
| DELETE | `/api/fitness/profile` | Delete caller's fitness profile and its schedules/progress, leaving the VitroFit account intact |
| GET | `/api/fitness/exercises` | Read approved exercise catalog |
| POST | `/api/fitness/workflows` | Start the first beginner schedule or generate the next workout block from recorded progress |
| GET | `/api/fitness/workflows?page=1&status=...` | Paginated caller-owned schedules |
| GET | `/api/fitness/workflows/{id}` | Read caller's schedule |
| GET | `/api/fitness/workflows/{id}/history` | Audit and progress history |
| POST | `/api/fitness/workflows/{id}/retry` | Retry eligible failed/interrupted member run |
| PUT | `/api/fitness/workflows/{id}/progress` | Record a workout, effort, pain status, and affected body areas |
| GET | `/api/fitness/workflows/{id}/next-cycle` | Read the three-month analysis window and its progress summary |
| POST | `/api/fitness/workflows/{id}/next-cycle` | Save a cycle review and start an analysis period; request body includes pain, injuries, current condition, goal, available minutes, and equipment |

The Python service exposes `/internal/generate` only to ASP.NET and has no browser CORS. The internal progress-event callback uses the same service key. API-generated secrets are configuration, never source values.

## Evaluation

Python golden tests:

```powershell
python -m pytest -q -p no:cacheprovider
```

Backend policy regression checks:

```powershell
dotnet run --project BackendAPI/FitnessAgent.Tests
```

Also build the API and React application, analyze the Flutter app where Flutter SDK is available, and perform a local PostgreSQL integration run. Demonstration scenario: member completes and records the four beginner schedules; answers the cycle review; receives only the next 3 or 4 workout days; records effort and any pain area; then receives the next adapted block. At the three-month boundary, the app summarizes that period and asks the review questions again. Capture only facts actually verified during your own run for your evaluation evidence and AI usage log.

## Ownership and limits

ASP.NET/EF Core owns fitness profiles, catalog, workflow records, plan versions, progress, and audit events. Python owns orchestration and LangGraph checkpoint storage. Both use the existing `DefaultConnection` database. Fitness table changes are isolated in this context's `fitness` schema and `__FitnessMigrationsHistory`; existing application migrations are separate.

Current limits: generation is synchronous with a bounded HTTP timeout; checkpoint state is durable, while the API retry route begins a new run rather than resuming a partially completed node. The feature is for adult beginners and is not medical clearance. The exercise catalog and conservative rules need qualified review before production use.
