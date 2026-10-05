# vitrofit_mobile

The VitroFit mobile app: a mirror of the VitroFit web app that talks to the same ASP.NET backend
(`/api`, JWT auth). The bottom bar has six tabs:

| Tab | What it does | Backend |
| --- | --- | --- |
| Home | Overview and shortcuts | `/api/timetable` (next session) |
| Fitness | Fitness agent: profile, week-by-week plans, progress, 3-month blocks | `/api/fitness/*` |
| Gym | Gym agent: nearby gyms, details, workout suggestions | `/api/gyms/*` |
| Diet | Diet agent: AI meal plans, refine, save; Trainer/Admin approvals queue | `/api/diet/*` |
| Time | Time Management agent: AI timetable from a Ready fitness plan, editable by hand | `/api/fitness/workflows/{id}/timetable`, `/api/timetable` |
| Profile | Account and settings | `/api/auth/*` |

The app never calls the Python agent services directly; everything goes through the ASP.NET API, which
holds the agents' service keys. So the only thing to point at a deployed backend is the API base URL.

## Pointing the app at a backend

The base URL is set at build/run time (no `.env` needed in the app):

```
# deployed backend (same one the web app uses)
flutter run --dart-define=API_BASE_URL=https://your-api.example.com/api
flutter build apk --dart-define=API_BASE_URL=https://your-api.example.com/api

# local backend on an Android emulator (default: needs `adb reverse tcp:5284 tcp:5284`)
flutter run
# local backend on a physical device (same Wi-Fi)
flutter run --dart-define=API_BASE_URL=http://192.168.1.20:5284/api
```

Each agent's own settings (LLM keys, service keys, database) stay in that agent's `.env` under
`BackendAPI/` (e.g. `DietPlanService/.env`, `FitnessAgentService/.env`,
`TimeManagementAgentService/.env`, `GymAgentService/.env`). The Time Management agent listens on
port 8004 (`TIME_MANAGEMENT_PORT`) and the API reaches it via `TimeManagementAgent:BaseUrl`; the Diet
agent keeps port 8003.

## Google Maps setup (Find Gym)

The Find Gym screen uses the Google Maps SDK for Android and the Places API (New).

1. In Google Cloud, enable **Maps SDK for Android** and **Places API (New)** (billing must be on).
2. Create a native map key restricted to the Android app (package `com.example.vitrofit_mobile` + your SHA-1)
   and to Maps SDK for Android. A key restricted to website referrers (the web app's key) will be refused here.
3. Put the key where the native map reads it, in `android/local.properties` (git-ignored):

   ```
   MAPS_API_KEY=your_key_here
   ```

4. Place search needs no key in the app: it calls the VitroFit API (`POST /api/gyms/nearby`), which
   forwards to GymAgentService. Put the Places key there, in `BackendAPI/GymAgentService/.env`:

   ```
   GOOGLE_PLACES_API_KEY=your_key_here
   ```

   Restrict that key to **Places API (New)** (and to the server's IP if it has a fixed one), then restart
   GymAgentService.

Geoapify is no longer used. Gym details and workouts still come from the ASP.NET API.
