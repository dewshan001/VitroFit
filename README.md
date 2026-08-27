# VitroFit

VitroFit is a fitness platform with a **.NET Web API backend**, a **React (Vite) web frontend**, and a **Flutter mobile app**. This guide covers how to run the **backend** and the **web frontend** on your local machine. (The mobile app is not covered here.)

---

## Table of Contents

- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [1. Running the Backend API](#1-running-the-backend-api)
- [2. Running the Web Frontend](#2-running-the-web-frontend)
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

---

## Project Structure

```
VitroFit/
├── BackendAPI/
│   └── VitroFit.API/            # ASP.NET Core Web API (backend)
│       ├── Controllers/         # AuthController, AdminController
│       ├── Data/                # EF Core DbContext
│       ├── Dtos/                # Auth + Admin request/response models
│       ├── Entities/            # User, RefreshToken, PasswordResetOtp, enums
│       ├── Migrations/          # EF Core SQL migrations
│       ├── Services/            # Auth, Token, Email (MailKit), Cloudinary image
│       ├── Settings/            # Jwt, Cloudinary, Email strongly-typed config
│       ├── Program.cs           # App startup, DI, pipeline, JWT, CORS
│       └── appsettings.json     # Config: DB, JWT, SMTP, Cloudinary
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

## Both Apps at a Glance

| App | Command | URL |
| --- | --- | --- |
| Backend API | `dotnet run` (in `BackendAPI/VitroFit.API`) | `http://localhost:5284` |
| API Swagger | — | `http://localhost:5284/swagger` |
| Web frontend | `npm run dev` (in `VitroFit_web`) | `http://localhost:5173` |

The web app must be running while the backend is running in order to see real
data (login, register, admin dashboard, profile).

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

---

## Configuration Reference

The web's `.env` defines the API base URL. The backend's `appsettings.json`
defines the database connection, JWT, SMTP and Cloudinary settings. For basic
local development you only need to set the database connection string and a JWT
secret; SMTP and Cloudinary are only used by specific features (email OTPs and
profile photo uploads).

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
The API uses `5284` (and `7176` for HTTPS) and Vite uses `5173`. If any of
these are taken, adjust the `applicationUrl` in `launchSettings.json` and the
`.env`, respectively.