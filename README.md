# VitroFit

VitroFit is a fitness platform with a **.NET Web API backend**, three **Python (FastAPI) microservices** for gym enrichment, chatbot, and diet plan features, a **React (Vite) web frontend**, and a **Flutter mobile app**. This guide covers how to run the **backend**, **microservices**, and the **web frontend** on your local machine. (The mobile app is not covered here.)

---

## Table of Contents

- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [1. Running the Backend API](#1-running-the-backend-api)
- [2. Running the Web Frontend](#2-running-the-web-frontend)
- [3. Running the Python Microservices](#3-running-the-python-microservices-optional-but-required-for-find-gyms--chatbot--diet-plans)
- [Both Apps at a Glance](#both-apps-at-a-glance)
- [API Endpoints](#api-endpoints)
- [Configuration Reference](#configuration-reference)
- [Default Admin Account](#default-admin-account)
- [Troubleshooting](#troubleshooting)

---

## Tech Stack

| Layer | Technology |
| ----- | ---------- |
| **Backend** | ASP.NET Core (.NET 10), Entity Framework Core, PostgreSQL (Npgsql), JWT Bearer auth, Swagger/OpenAPI, MailKit (SMTP), Cloudinary (image hosting) |
| **Web** | React 19, Vite 8, React Router 7, Three.js (react-three-fiber / drei), GSAP, Framer Motion |
| **Microservices** | Python (FastAPI, Uvicorn), SQLAlchemy + psycopg2 (GymAgentService, DietPlanService), OpenRouter (OpenAI-compatible client) for gym enrichment, Google AI Studio (Gemini/Gemma via `google-genai`) for the chatbot and diet plan agent |

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
│   └── DietPlanService/         # FastAPI: AI nutrition/diet plan agent (port 8002)
├── VitroFit_web/                # React (Vite) web frontend
│   ├── src/
│   │   ├── api/                 # auth.js, admin.js API client
│   │   ├── components/          # Navbar, Hero, ClassesList, Footer, ...
│   │   ├── hooks/               # useAuth, useScrollAnimation
│   │   ├── pages/               # Home, About, Classes, Login, Profile, Admin, ...
│   │   └── App.jsx              # Route definitions
│   ├── .env                     # VITE_API_BASE_URL
│   └── package.json
├── vitrofit_mobile/             # Flutter mobile app (NOT covered in this guide)
└── README.md
```

---

## Prerequisites

Make sure the following are installed on your machine:

| Tool | Version required | Check with |
| ---- | ---------------- | ---------- |
| **.NET SDK** | 10.0+ | `dotnet --version` |
| **Node.js** | 20+ (LTS) | `node --version` |
| **npm** | 9+ | `npm --version` |
| **PostgreSQL** | 13+ | running locally on **port 5432** |
| **Python** | 3.12+ | `python --version` (only needed for the Find Gyms / Chatbot microservices) |
---

## Optional: One-command dependency install

From the repository root you can install **all** backend and web dependencies with
a single script (Windows / PowerShell):

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

This runs `dotnet restore` (backend) and `npm install` (web) for you. It does
**not** start the apps or configure credentials — follow the sections below for
that. Manual installs are also documented in each section.

---

## 1. Running the Backend API

### 1.1 Configure `appsettings.json`

Backend config lives in
`BackendAPI/VitroFit.API/appsettings.json`. Before the app can start you must set:

**a) Database connection string**

Under `ConnectionStrings → DefaultConnection`, match the PostgreSQL instance on
your machine. The current default is:

```json
"DefaultConnection": "Host=localhost;Database=VitroFit;Port=5432;Username=postgres;Password=12345678"
```

If your Postgres uses different credentials, update this value.

**b) JWT secret**

Replace the placeholder in `JwtSettings → Secret` with a long random string
(at least 32 characters):

```json
"JwtSettings": {
  "Secret": "REPLACE_WITH_A_LONG_RANDOM_SECRET_KEY",
  "Issuer": "VitroFitApi",
  "Audience": "VitroFitWeb",
  "AccessTokenExpirationMinutes": 60,
  "RefreshTokenExpirationDays": 30
}
```

**c) Email (SMTP) — required for registration / forgot-password OTPs**

When a user registers or resets a password the API emails a 6-digit OTP using
the `EmailSettings` section. For Gmail use an **App Password**
(see <https://myaccount.google.com/apppasswords>), not your Google password.

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

**d) Cloudinary — only if uploading profile photos**

`Cloudinary` settings are used by the `POST /api/auth/me/photo` endpoint. If you
don't need profile photo uploads you can leave the values as-is for development.

### 1.2 Restore packages

```bash
cd BackendAPI/VitroFit.API
dotnet restore
```

### 1.3 Create the database

The schema is managed with EF Core migrations (already present in the `Migrations/`
folder). On startup the API **automatically applies any pending migrations and
creates the database if needed** (via `context.Database.Migrate()`), so you normally
don't need to run anything manually:

```bash
dotnet run
```

If you prefer to create/update the database explicitly (for example to inspect the
schema before starting the API), you can do so with:

```bash
dotnet ef database update
```

> On startup the API also seeds a system admin account automatically
> (see [Default Admin Account](#default-admin-account)).

### 1.4 Run the API

```bash
dotnet run
```

By default the API starts on:

- **HTTP:** `http://localhost:5284`
- **HTTPS:** `https://localhost:7176`

The web frontend expects the API at `http://localhost:5284/api`.

Swagger UI is available (in Development) at:

- **http://localhost:5284/swagger**
---
## 2. Running the Web Frontend

### 2.1 Install dependencies

```bash
cd VitroFit_web
npm install
```

### 2.2 Check the API base URL (`.env`)

The web app reads the API base URL from `VitroFit_web/.env`:

```
VITE_API_BASE_URL=http://localhost:5284/api
```

Make sure this points to the backend that is currently running. If you changed
the backend port, update this value (then restart the dev server).

### 2.3 Start the dev server

```bash
npm run dev
```

By default Vite serves the app at **http://localhost:5173**.

You can also run `npm run build` to create a production bundle, then
`npm run preview` to preview it. `npm run lint` runs the oxlint static checks.

---

## 3. Running the Python Microservices (optional but required for Find Gyms / Chatbot / Diet Plans)

Three small FastAPI services live under `BackendAPI/` and power specific web
features by being called **directly from the browser** (not proxied through
`VitroFit.API`):

| Service | Port | Powers | Frontend call site |
| ------- | ---- | ------ | ------------------- |
| `GymAgentService` | `8001` | "Find Gyms" equipment/classes enrichment | `VitroFit_web/src/api/gyms.js` |
| `chatbot_service` | `8000` | The RAG fitness chatbot widget | `VitroFit_web/src/components/Chatbot/Chatbot.jsx` |
| `DietPlanService` | `8002` | The AI diet/nutrition plan agent | `VitroFit_web/src/api/dietPlan.js` |

### 3.1 Auto-start with the backend

`VitroFit.API` tries to launch all three services automatically on `dotnet run`
(see `Program.cs`): if a service's `venv` exists and its port is free, the API
starts it with `python -m uvicorn main:app --port <port>` and stops it when
the API shuts down. If the `venv` isn't set up yet, this is skipped with a
warning in the API logs — it does **not** fail backend startup. So once you've
done the one-time setup below, `dotnet run` in `VitroFit.API` is enough for
day-to-day use.

### 3.2 One-time setup

**GymAgentService:**

```bash
cd BackendAPI/GymAgentService
python -m venv venv
venv/Scripts/pip install -r requirements.txt   # venv/bin/pip on macOS/Linux
copy .env.example .env                          # cp on macOS/Linux, then fill in values
```

Required `.env` values: `DATABASE_URL` (same Postgres instance/DB as the
backend), `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `PORT` (`8001`),
`CACHE_STALE_DAYS` (how long a cached enrichment result is reused).

**chatbot_service:**

```bash
cd BackendAPI/chatbot_service
python -m venv venv
venv/Scripts/pip install -r requirements.txt   # venv/bin/pip on macOS/Linux
copy .env.example .env                          # cp on macOS/Linux, then fill in values
```

Required `.env` values: `GOOGLE_API_KEY` (get one at
[Google AI Studio](https://aistudio.google.com/apikey)), and optionally
`GEMINI_MODEL_PRIMARY` / `GEMINI_MODEL_FALLBACK` if you want to override the
default Gemma models. This service uses
[Google AI Studio](https://ai.google.dev/) (via the `google-genai` SDK) as its
LLM provider, while `GymAgentService` uses [OpenRouter](https://openrouter.ai/)
(via an OpenAI-compatible client) — get an API key from whichever provider(s)
you need.

> If you see `ValueError: No API key was provided` when starting
> `chatbot_service`, it means `GOOGLE_API_KEY` is missing or empty in its
> `.env` file — copy `.env.example` to `.env` (if you haven't already) and
> set a valid key.

**DietPlanService:**

```bash
cd BackendAPI/DietPlanService
python -m venv venv
venv/Scripts/pip install -r requirements.txt   # venv/bin/pip on macOS/Linux
copy .env.example .env                          # cp on macOS/Linux, then fill in values
```

Required `.env` values: `DATABASE_URL` (same Postgres instance/DB as the
backend), `DIET_GOOGLE_API_KEY` (a **separate** Google AI Studio key from
`chatbot_service`'s — get one at
[Google AI Studio](https://aistudio.google.com/apikey) — so the two services
don't share/exhaust the same quota), optionally `GEMINI_MODEL_PRIMARY` /
`GEMINI_MODEL_FALLBACK`, and `JWT_SIGNING_KEY` / `JWT_ISSUER` / `JWT_AUDIENCE`
which must match `VitroFit.API`'s `appsettings.json` → `JwtSettings` exactly
(this service verifies the same access tokens the .NET backend issues, since
it writes user-linked data).

### 3.3 Running manually

Auto-start covers normal use; to run a service standalone (e.g. before its
`venv` exists, or to see its logs directly):

```bash
# from BackendAPI/GymAgentService
venv/Scripts/python -m uvicorn main:app --port 8001

# from BackendAPI/chatbot_service
venv/Scripts/python -m uvicorn main:app --port 8000

# from BackendAPI/DietPlanService
venv/Scripts/python -m uvicorn main:app --port 8002
```

Check any of them is up with `GET http://localhost:<port>/health`.

---

## Both Apps at a Glance

| App | Command | URL |
| --- | --- | --- |
| Backend API | `dotnet run` (in `BackendAPI/VitroFit.API`) | `http://localhost:5284` |
| API Swagger | — | `http://localhost:5284/swagger` |
| Web frontend | `npm run dev` (in `VitroFit_web`) | `http://localhost:5173` |
| Gym Agent service | auto-started by the API, or manual (see [§3](#3-running-the-python-microservices-optional-but-required-for-find-gyms--chatbot--diet-plans)) | `http://localhost:8001` |
| Chatbot service | auto-started by the API, or manual (see [§3](#3-running-the-python-microservices-optional-but-required-for-find-gyms--chatbot--diet-plans)) | `http://localhost:8000` |
| Diet Plan service | auto-started by the API, or manual (see [§3](#3-running-the-python-microservices-optional-but-required-for-find-gyms--chatbot--diet-plans)) | `http://localhost:8002` |

The web app must be running while the backend is running in order to see real
data (login, register, admin dashboard, profile). The three Python services
are only needed for the Find Gyms, Chatbot, and Diet Plan features
respectively.

---
## API Endpoints

All routes are under the `/api` prefix and are defined in the `Controllers/`
folder.

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

> 🔒 = requires a valid `Authorization: Bearer <access token>` header.

### Admin — `/api/admin` (requires the `Admin` role)

| Method | Route | Description |
| ------ | ----- | ----------- |
| GET | `/admin/users?role=` | List users (optionally filter by `role`) |
| POST | `/admin/users` | Create a user (auto-verified) |
| DELETE | `/admin/users/{id}` | Delete a user (cannot delete yourself) |

### Gym Agent — `http://localhost:8001` (separate service, called directly by the web app)

| Method | Route | Description |
| ------ | ----- | ----------- |
| GET | `/health` | Health check |
| POST | `/api/gyms/details` | Get (and cache) enriched equipment/classes for a gym |

### Chatbot — `http://localhost:8000` (separate service, called directly by the web app)

| Method | Route | Description |
| ------ | ----- | ----------- |
| GET | `/health` | Health check |
| POST | `/api/chat` | Ask the RAG fitness chatbot; streams a `text/event-stream` response |

### Diet Plan Agent — `http://localhost:8002` (separate service, called directly by the web app)

| Method | Route | Auth | Description |
| ------ | ----- | ---- | ----------- |
| GET | `/health` | — | Health check |
| POST | `/api/diet/generate` | 🔒 | Compute calorie/macro targets and generate a meal plan from the given preferences (not saved) |
| POST | `/api/diet/confirm` | 🔒 | Save a (possibly user-edited) generated plan, plus the inputs that produced it |

> 🔒 = requires the same `Authorization: Bearer <access token>` header issued by `VitroFit.API`; this service verifies it independently (see [§3.2](#32-one-time-setup)).

---

## Configuration Reference

The web's `.env` (copy from `VitroFit_web/.env.example`) defines the API base
URLs: `VITE_API_BASE_URL` (the .NET backend), and `VITE_GYM_AGENT_API_URL` /
`VITE_CHATBOT_API_URL` / `VITE_DIET_AGENT_API_URL` (the Python services,
defaulting to `http://localhost:8001/api`, `http://localhost:8000/api/chat`,
and `http://localhost:8002/api/diet` respectively if unset). The backend's
`appsettings.json` defines the database connection, JWT, SMTP and Cloudinary
settings. Each Python microservice has its own `.env` (copy from the
`.env.example` in its folder): `GymAgentService` needs `DATABASE_URL` and
`OPENROUTER_API_KEY`; `chatbot_service` needs `GOOGLE_API_KEY`;
`DietPlanService` needs `DATABASE_URL`, `DIET_GOOGLE_API_KEY`, and
`JWT_SIGNING_KEY`/`JWT_ISSUER`/`JWT_AUDIENCE` matching the backend's
`JwtSettings`. For basic local development you only need to set the database
connection string and a JWT secret; SMTP, Cloudinary, and the Python
services' API keys are only used by specific features (email OTPs, profile
photo uploads, and Find Gyms / Chatbot / Diet Plans).

---

## Default Admin Account

On startup the API automatically seeds an admin user:

| Field | Value |
| ----- | ----- |
| Email | `admin@gmail.com` |
| Password | `admin1234` |

This account is **email-verified** and has the **Admin** role, so you can log in
to the web app at `/login` and access the admin dashboard at `/admin`.

> Change these credentials in production.

---

## Troubleshooting

**The web app cannot talk to the API.**
Make sure the backend is running and that `VITE_API_BASE_URL` in the web `.env`
matches the backend port (default `http://localhost:5284/api`). Restart the
Vite dev server after editing `.env`.

**Login fails with "Please verify your email…".**
New registrations must verify their email via the OTP sent by the backend.
Until then `login` is blocked. Use the verification step in the UI or the
`/auth/verify-email` endpoint.

**No OTP email arrives.**
Check the inbox (and spam) and confirm `EmailSettings` carries a valid
SMTP/App password.

**Database errors — `Host=localhost` connection refused.**
Confirm PostgreSQL is running on port 5432 and that the credentials in
`ConnectionStrings → DefaultConnection` are correct. The schema is created and
updated automatically when the API starts, so just run `dotnet run` again.

**Port already in use.**
The API uses `5284` (and `7176` for HTTPS), Vite uses `5173`, the Gym Agent
service uses `8001`, and the chatbot service uses `8000`. If any of these are
taken, adjust the `applicationUrl` in `launchSettings.json`, the web `.env`,
or the relevant service's `.env`/`PORT`, respectively.

**Find Gyms or the chatbot doesn't respond.**
Check the `VitroFit.API` startup logs for a "venv not found — skipping
auto-start" warning — if you see it, follow the one-time setup in
[§3.2](#32-one-time-setup) for that service. If the `venv` exists but the
feature still fails, confirm the service's `.env` (copied from its
`.env.example`) has a valid API key — `OPENROUTER_API_KEY` for
`GymAgentService`, `GOOGLE_API_KEY` for `chatbot_service` — or start it
manually (see [§3.3](#33-running-manually)) to see its logs directly. You can
also hit its `/health` endpoint to confirm it's up.

**`chatbot_service` crashes with `ValueError: No API key was provided`.**
`GOOGLE_API_KEY` is missing or empty. Run
`copy .env.example .env` (or `cp` on macOS/Linux) inside
`BackendAPI/chatbot_service` if you haven't yet, then set `GOOGLE_API_KEY` to
a key from [Google AI Studio](https://aistudio.google.com/apikey) and restart
the service.