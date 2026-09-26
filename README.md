# VitroFit

Fitness platform with a .NET Web API backend, four Python (FastAPI) microservices, a React (Vite) web frontend, and a Flutter mobile app. This guide covers running the backend, microservices, and web frontend locally. The mobile app is not covered here.

---

## Table of Contents

- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [1. Backend API](#1-backend-api)
- [2. Web Frontend](#2-web-frontend)
- [3. Python Microservices](#3-python-microservices)
- [4. Adaptive Fitness Agent](#4-adaptive-fitness-agent)
- [Services at a Glance](#services-at-a-glance)
- [API Endpoints](#api-endpoints)
- [Configuration Reference](#configuration-reference)
- [Default Admin Account](#default-admin-account)
- [Troubleshooting](#troubleshooting)

---

## Tech Stack

| Layer | Technology |
| ----- | ---------- |
| Backend | ASP.NET Core (.NET 10), Entity Framework Core, PostgreSQL (Npgsql), JWT Bearer auth, Swagger/OpenAPI, MailKit (SMTP), Cloudinary (image hosting) |
| Web | React 19, Vite 8, React Router 7, Three.js (react-three-fiber / drei), GSAP, Framer Motion |
| Microservices | Python (FastAPI, Uvicorn), SQLAlchemy + psycopg2 (GymAgentService, DietPlanService). Providers: OpenRouter (gym enrichment, adaptive fitness agent), Google AI Studio / Gemini via `google-genai` (chatbot), NVIDIA API (diet plan agent). Adaptive fitness agent uses LangGraph with PostgreSQL checkpoints |

---

## Project Structure

```
VitroFit/
├── BackendAPI/
│   ├── VitroFit.API/            # ASP.NET Core Web API (backend)
│   │   ├── Controllers/         # AuthController, AdminController
│   │   ├── Data/                # EF Core DbContext
│   │   ├── Dtos/                # Auth + Admin request/response models
│   │   ├── Entities/            # User, RefreshToken, PasswordResetOtp, enums
│   │   ├── Migrations/          # EF Core SQL migrations
│   │   ├── Services/            # Auth, Token, Email (MailKit), Cloudinary image
│   │   ├── Settings/            # Jwt, Cloudinary, Email strongly-typed config
│   │   ├── Program.cs           # App startup, DI, pipeline, JWT, CORS, Python sidecar auto-start
│   │   └── appsettings.json     # Config: DB, JWT, SMTP, Cloudinary
│   ├── GymAgentService/         # FastAPI: nearby-gym equipment/classes enrichment (port 8001)
│   ├── chatbot_service/         # FastAPI: RAG fitness chatbot, streamed responses (port 8000)
│   ├── DietPlanService/         # FastAPI: AI nutrition/diet plan agent (port 8003)
│   └── FitnessAgentService/     # FastAPI/LangGraph: adaptive fitness agent (port 8002)
├── VitroFit_web/                # React (Vite) web frontend
│   ├── src/
│   │   ├── api/                 # auth.js, admin.js API client
│   │   ├── components/          # Navbar, Hero, ClassesList, Footer, ...
│   │   ├── hooks/                # useAuth, useScrollAnimation
│   │   ├── pages/                # Home, About, Classes, Login, Profile, Admin, ...
│   │   └── App.jsx              # Route definitions
│   ├── .env                     # VITE_API_BASE_URL
│   └── package.json
├── vitrofit_mobile/              # Flutter mobile app (not covered in this guide)
└── README.md
```

---

## Prerequisites

| Tool | Version | Check with |
| ---- | ------- | ---------- |
| .NET SDK | 10.0+ | `dotnet --version` |
| Node.js | 20+ (LTS) | `node --version` |
| npm | 9+ | `npm --version` |
| PostgreSQL | 13+ | running locally on port 5432 |
| Python | 3.12+ | `python --version` (needed for the Python microservices) |

---

## 1. Backend API

### 1.1 Configure `appsettings.json`

Backend config lives in `BackendAPI/VitroFit.API/appsettings.json`. Set the following before starting:

**Database connection string** — under `ConnectionStrings → DefaultConnection`, match your local PostgreSQL instance. Default:

```json
"DefaultConnection": "Host=localhost;Database=VitroFit;Port=5432;Username=postgres;Password=12345678"
```

**JWT secret** — replace the placeholder in `JwtSettings → Secret` with a random string of at least 32 characters:

```json
"JwtSettings": {
  "Secret": "REPLACE_WITH_A_LONG_RANDOM_SECRET_KEY",
  "Issuer": "VitroFitApi",
  "Audience": "VitroFitWeb",
  "AccessTokenExpirationMinutes": 60,
  "RefreshTokenExpirationDays": 30
}
```

**Email (SMTP)** — required for registration / forgot-password OTPs. Configure `EmailSettings`. For Gmail, use an [App Password](https://myaccount.google.com/apppasswords), not your account password:

```json
"EmailSettings": {
  "Host": "smtp.gmail.com",
  "Port": 587,
  "UseSsl": false,
  "Username": "you@gmail.com",
  "Password": "your-app-password",
  "SenderName": "VitroFit",
  "SenderEmail": "you@gmail.com"
}
```

**Cloudinary** — used by `POST /api/auth/me/photo`. Only needed for profile photo uploads; leave as-is otherwise.

### 1.2 Restore packages

```bash
cd BackendAPI/VitroFit.API
dotnet restore
```

### 1.3 Database

Schema is managed via EF Core migrations (in `Migrations/`). On startup the API automatically applies pending migrations and creates the database if needed (`context.Database.Migrate()`), so no manual step is required. To apply migrations explicitly without starting the API:

```bash
dotnet ef database update
```

A system admin account is seeded automatically on startup — see [Default Admin Account](#default-admin-account).

### 1.4 Run

```bash
dotnet run
```

- HTTP: `http://localhost:5284`
- HTTPS: `https://localhost:7176`
- Swagger UI (Development): `http://localhost:5284/swagger`

The web frontend expects the API at `http://localhost:5284/api`.

---

## 2. Web Frontend

```bash
cd VitroFit_web
npm install
```

Set the API base URL in `VitroFit_web/.env`:

```
VITE_API_BASE_URL=http://localhost:5284/api
```

Start the dev server:

```bash
npm run dev
```

Vite serves the app at `http://localhost:5173`. `npm run build` creates a production bundle, `npm run preview` previews it, and `npm run lint` runs oxlint.

---

## 3. Python Microservices

Three FastAPI services live under `BackendAPI/` and are called directly from the browser (not proxied through `VitroFit.API`):

| Service | Port | Powers | Frontend call site |
| ------- | ---- | ------ | ------------------- |
| `GymAgentService` | 8001 | "Find Gyms" equipment/classes enrichment | `VitroFit_web/src/api/gyms.js` |
| `chatbot_service` | 8000 | RAG fitness chatbot widget | `VitroFit_web/src/components/Chatbot/Chatbot.jsx` |
| `DietPlanService` | 8003 | AI diet/nutrition plan agent | `VitroFit_web/src/api/dietPlan.js` |

### 3.1 Auto-start with the backend

`VitroFit.API` launches all three on `dotnet run` (see `Program.cs`): if a service's `venv` exists and its port is free, the API starts it with `python -m uvicorn main:app --port <port>` and stops it on shutdown. If a `venv` isn't set up, startup is skipped for that service with a warning in the API logs — backend startup itself does not fail.

### 3.2 One-time setup

**GymAgentService:**

```bash
cd BackendAPI/GymAgentService
python -m venv venv
venv/Scripts/pip install -r requirements.txt   # venv/bin/pip on macOS/Linux
copy .env.example .env                          # cp on macOS/Linux, then fill in values
```

Required `.env` values: `DATABASE_URL` (same Postgres instance/DB as the backend), `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `PORT` (`8001`), `CACHE_STALE_DAYS`.

**chatbot_service:**

```bash
cd BackendAPI/chatbot_service
python -m venv venv
venv/Scripts/pip install -r requirements.txt   # venv/bin/pip on macOS/Linux
copy .env.example .env                          # cp on macOS/Linux, then fill in values
```

Required `.env` values: `GOOGLE_API_KEY` (get one at [Google AI Studio](https://aistudio.google.com/apikey)), and optionally `GEMINI_MODEL_PRIMARY` / `GEMINI_MODEL_FALLBACK` to override the default Gemma models.

> `ValueError: No API key was provided` on startup means `GOOGLE_API_KEY` is missing — copy `.env.example` to `.env` and set a valid key.

**DietPlanService:**

```bash
cd BackendAPI/DietPlanService
python -m venv venv
venv/Scripts/pip install -r requirements.txt   # venv/bin/pip on macOS/Linux
copy .env.example .env                          # cp on macOS/Linux, then fill in values
```

Required `.env` values: `DATABASE_URL` (same Postgres instance/DB as the backend), `NVIDIA_API_KEY` (get one at [build.nvidia.com](https://build.nvidia.com/)), and optionally `NVIDIA_MODEL_PRIMARY` / `NVIDIA_MODEL_FALLBACK`. JWT verification needs no `.env` entry — this service reads the signing key/issuer/audience directly from `VitroFit.API`'s `appsettings.json` → `JwtSettings` at startup, so that folder must exist alongside `DietPlanService` with a valid `appsettings.json`.

### 3.3 Running manually

To run a service standalone (e.g. before its `venv` exists, or to see its logs directly):

```bash
# from BackendAPI/GymAgentService
venv/Scripts/python -m uvicorn main:app --port 8001

# from BackendAPI/chatbot_service
venv/Scripts/python -m uvicorn main:app --port 8000

# from BackendAPI/DietPlanService
venv/Scripts/python -m uvicorn main:app --port 8003
```

Check any service with `GET http://localhost:<port>/health`.

---

## 4. Adaptive Fitness Agent

A dedicated Python FastAPI/LangGraph service proposes beginner workout schedules. The web app calls `VitroFit.API`, which calls this agent; browsers never call it directly. It listens on `127.0.0.1:8002`.

### Prerequisites

- Python 3.12+
- PostgreSQL running with the same local VitroFit database as ASP.NET (`ConnectionStrings:DefaultConnection`)
- An OpenRouter API key and an available model ID
- .NET SDK 10 and Node.js for the API and web app

### Configure

From the repository root:

```powershell
Copy-Item BackendAPI/FitnessAgentService/.env.example BackendAPI/FitnessAgentService/.env
py -3.12 -m venv BackendAPI/FitnessAgentService/.venv
BackendAPI/FitnessAgentService/.venv/Scripts/python.exe -m pip install -r BackendAPI/FitnessAgentService/requirements.txt
```

Edit `BackendAPI/FitnessAgentService/.env`:

| Variable | Value |
| --- | --- |
| `FITNESS_SERVICE_KEY` | Random secret, 32+ characters. Must match ASP.NET's value exactly. |
| `FITNESS_API_URL` | ASP.NET base URL, normally `http://127.0.0.1:5284` (no `/api` suffix). |
| `FITNESS_DATABASE_URL` | PostgreSQL URL for the same local database as ASP.NET, e.g. `postgresql://postgres:<password>@127.0.0.1:5432/VitroFit?sslmode=disable`. |
| `OPENROUTER_API_KEY` | Your OpenRouter API key. |
| `OPENROUTER_MODEL` | A model identifier enabled for your OpenRouter account. |

Keep `.env` local; never commit API keys or service secrets.

Configure the matching key and agent URL for ASP.NET (from `BackendAPI/VitroFit.API`):

```powershell
dotnet user-secrets init
dotnet user-secrets set 'FitnessAgent:ServiceKey' '<the-same-random-secret>'
dotnet user-secrets set 'FitnessAgent:BaseUrl' 'http://127.0.0.1:8002'
```

If User Secrets aren't configured, use environment variables `FitnessAgent__ServiceKey` and `FitnessAgent__BaseUrl` instead. Do not put production secrets in committed `appsettings.json`.

### Apply the fitness database migrations

The fitness feature uses the existing PostgreSQL database in a separate `fitness` schema — no second database is needed. Verify the connection string, then from `BackendAPI/VitroFit.API`:

```powershell
dotnet ef database update --context FitnessDbContext
```

This migration is separate from the API's normal startup migrations. Do not apply it to a shared or deployed database without review.

### Start the services

```powershell
# Terminal 1: ASP.NET API (port 5284)
Set-Location BackendAPI/VitroFit.API
dotnet run
```

```powershell
# Terminal 2: Adaptive Fitness Python agent
Set-Location BackendAPI/FitnessAgentService
.\.venv\Scripts\python.exe -m app.server
```

```powershell
# Terminal 3: React web app
Set-Location VitroFit_web
npm run dev
```

Open `http://localhost:5173`, sign in with a verified account, and visit `/adaptive-fitness`. Agent health check: `http://127.0.0.1:8002/health`.

### Tests

`BackendAPI/FitnessAgent.Tests` is the .NET regression-test project for the Adaptive Fitness API's planning and safety rules (rejecting unsafe profiles, mismatched exercises, invalid schedules, excessive progression). Not required to run the API or agent, but keep it in Git to catch regressions.

```powershell
# .NET tests, from the repository root
dotnet run --project BackendAPI/FitnessAgent.Tests

# Agent tests, from BackendAPI/FitnessAgentService
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

If fitness requests return `503`: confirm the Python agent and ASP.NET API are running, the fitness migration is applied, and `FitnessAgent:BaseUrl` points to port `8002`. A `401` from the agent usually means `FITNESS_SERVICE_KEY` and `FitnessAgent:ServiceKey` don't match. Provider `401`/`403` means an invalid OpenRouter key or model permission; `402` means unavailable credits; `429` means rate limiting.

More endpoint contracts: [`BackendAPI/VitroFit.API/Features/AdaptiveFitness/README.md`](BackendAPI/VitroFit.API/Features/AdaptiveFitness/README.md).

---

## Services at a Glance

| Service | Command | URL |
| --- | --- | --- |
| Backend API | `dotnet run` (in `BackendAPI/VitroFit.API`) | `http://localhost:5284` |
| API Swagger | — | `http://localhost:5284/swagger` |
| Web frontend | `npm run dev` (in `VitroFit_web`) | `http://localhost:5173` |
| Gym Agent service | auto-started by the API, or manual ([§3](#3-python-microservices)) | `http://localhost:8001` |
| Chatbot service | auto-started by the API, or manual ([§3](#3-python-microservices)) | `http://localhost:8000` |
| Diet Plan service | auto-started by the API, or manual ([§3](#3-python-microservices)) | `http://localhost:8003` |
| Adaptive Fitness agent | auto-started by the API, or manual ([§4](#4-adaptive-fitness-agent)) | `http://127.0.0.1:8002` |

The web app needs the backend running to show real data (login, register, admin dashboard, profile). The Python services are only needed for Find Gyms, Chatbot, Diet Plan, and Adaptive Fitness respectively.

---

## API Endpoints

All routes are under `/api`, defined in the `Controllers/` folder.

### Auth — `/api/auth`

| Method | Route | Auth | Description |
| ------ | ----- | ---- | ----------- |
| POST | `/auth/register` | — | Create account, sends a 6-digit email-verification OTP |
| POST | `/auth/login` | — | Log in (email + password) → access + refresh tokens |
| POST | `/auth/verify-email` | — | Validate the email-verification OTP, activate account, returns tokens |
| POST | `/auth/resend-verification` | — | Re-send the email-verification OTP |
| POST | `/auth/refresh` | — | Exchange a refresh token for a new access token |
| GET | `/auth/me` | 🔒 | Get the current user's profile |
| POST | `/auth/me/photo` | 🔒 | Upload a profile photo (multipart `file`) |
| POST | `/auth/change-password` | 🔒 | Change the current user's password |
| DELETE | `/auth/me` | 🔒 | Delete the current user's account |
| POST | `/auth/forgot-password` | — | Step 1 – email an OTP to reset the password |
| POST | `/auth/reset-password` | — | Step 2 – reset the password with the OTP |

🔒 = requires `Authorization: Bearer <access token>`.

### Admin — `/api/admin` (requires the `Admin` role)

| Method | Route | Description |
| ------ | ----- | ----------- |
| GET | `/admin/users?role=` | List users (optionally filter by `role`) |
| POST | `/admin/users` | Create a user (auto-verified) |
| DELETE | `/admin/users/{id}` | Delete a user (cannot delete yourself) |

### Gym Agent — `http://localhost:8001` (separate service)

| Method | Route | Description |
| ------ | ----- | ----------- |
| GET | `/health` | Health check |
| POST | `/api/gyms/details` | Get (and cache) enriched equipment/classes for a gym |

### Chatbot — `http://localhost:8000` (separate service)

| Method | Route | Description |
| ------ | ----- | ----------- |
| GET | `/health` | Health check |
| POST | `/api/chat` | Ask the RAG fitness chatbot; streams a `text/event-stream` response |

### Diet Plan Agent — `http://localhost:8003` (separate service)

| Method | Route | Auth | Description |
| ------ | ----- | ---- | ----------- |
| GET | `/health` | — | Health check |
| POST | `/api/diet/generate` | 🔒 | Compute calorie/macro targets and generate a meal plan from the given preferences (not saved) |
| POST | `/api/diet/confirm` | 🔒 | Save a (possibly user-edited) generated plan, plus the inputs that produced it |
| GET | `/api/diet/plans` | 🔒 | List the current user's saved plans |
| PUT | `/api/diet/plans/{id}` | 🔒 | Update a saved plan |
| DELETE | `/api/diet/plans/{id}` | 🔒 | Delete a saved plan |

🔒 = requires the same access token issued by `VitroFit.API`; this service verifies it directly against `VitroFit.API`'s `appsettings.json` (see [§3.2](#32-one-time-setup)).

---

## Configuration Reference

- **Web** (`VitroFit_web/.env`, copy from `.env.example`): `VITE_API_BASE_URL` (the .NET backend), `VITE_GYM_AGENT_API_URL`, `VITE_CHATBOT_API_URL`, `VITE_DIET_AGENT_API_URL` (Python services — default to `http://localhost:8001/api`, `http://localhost:8000/api/chat`, `http://localhost:8003/api/diet` if unset).
- **Backend** (`appsettings.json`): database connection, JWT, SMTP, Cloudinary settings.
- **GymAgentService** (`.env`): `DATABASE_URL`, `OPENROUTER_API_KEY`.
- **chatbot_service** (`.env`): `GOOGLE_API_KEY`.
- **DietPlanService** (`.env`): `DATABASE_URL`, `NVIDIA_API_KEY`. JWT settings are read from `VitroFit.API`'s `appsettings.json`, not its own `.env`.

For basic local development you only need the database connection string and a JWT secret; SMTP, Cloudinary, and the Python services' API keys are only needed for their specific features (email OTPs, profile photo uploads, Find Gyms / Chatbot / Diet Plans).

---

## Default Admin Account

Seeded automatically on backend startup:

| Field | Value |
| ----- | ----- |
| Email | `admin@gmail.com` |
| Password | `admin1234` |

Email-verified, `Admin` role — sign in at `/login`, admin dashboard at `/admin`. Change these credentials in production.

---

## Troubleshooting

**Web app can't reach the API.** Confirm the backend is running and `VITE_API_BASE_URL` matches its port (default `http://localhost:5284/api`). Restart the Vite dev server after editing `.env`.

**Login fails with "Please verify your email…".** New registrations must verify email via OTP before login. Use the verification step in the UI or `/auth/verify-email`.

**No OTP email arrives.** Check inbox/spam and confirm `EmailSettings` has a valid SMTP/App password.

**Database errors — `Host=localhost` connection refused.** Confirm PostgreSQL is running on port 5432 and the credentials in `ConnectionStrings → DefaultConnection` are correct. Schema is created/updated automatically on API startup — just run `dotnet run` again.

**Port already in use.** API uses `5284` (`7176` for HTTPS), Vite uses `5173`, Gym Agent uses `8001`, chatbot uses `8000`, Diet Plan uses `8003`, Adaptive Fitness uses `8002`. Adjust `launchSettings.json`, the web `.env`, or the relevant service's `.env`/`PORT`.

**Find Gyms or the chatbot doesn't respond.** Check the `VitroFit.API` startup logs for a "venv not found — skipping auto-start" warning; if present, follow [§3.2](#32-one-time-setup) for that service. If the `venv` exists but the feature still fails, confirm the service's `.env` has a valid API key (`OPENROUTER_API_KEY` for GymAgentService, `GOOGLE_API_KEY` for chatbot_service), or run it manually ([§3.3](#33-running-manually)) to see its logs. `/health` confirms it's up.

**`chatbot_service` crashes with `ValueError: No API key was provided`.** `GOOGLE_API_KEY` is missing or empty. Copy `.env.example` to `.env` in `BackendAPI/chatbot_service`, set a valid key from [Google AI Studio](https://aistudio.google.com/apikey), and restart.
