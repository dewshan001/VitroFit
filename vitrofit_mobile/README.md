# vitrofit_mobile

A new Flutter project.

## Getting Started

This project is a starting point for a Flutter application.

A few resources to get you started if this is your first Flutter project:

- [Learn Flutter](https://docs.flutter.dev/get-started/learn-flutter)
- [Write your first Flutter app](https://docs.flutter.dev/get-started/codelab)
- [Flutter learning resources](https://docs.flutter.dev/reference/learning-resources)

For help getting started with Flutter development, view the
[online documentation](https://docs.flutter.dev/), which offers tutorials,
samples, guidance on mobile development, and a full API reference.

## Google Maps setup (Find Gym)

The Find Gym screen uses the Google Maps SDK for Android and the Places API (New).

1. In Google Cloud, enable **Maps SDK for Android** and **Places API (New)** (billing must be on).
2. Create an API key restricted to the Android app (package `com.example.vitrofit_mobile` + your SHA-1)
   and to those two APIs. A key restricted to website referrers (the web app's key) will be refused here.
3. Put the key where the native map reads it, in `android/local.properties` (git-ignored):

   ```
   MAPS_API_KEY=your_key_here
   ```

4. Pass the same key for place search at run/build time:

   ```
   flutter run --dart-define=GOOGLE_MAPS_API_KEY=your_key_here
   ```

   If you use an Android-restricted key, the Places request must also send the app's package and
   SHA-1 certificate headers (`X-Android-Package`, `X-Android-Cert`); add them in
   `lib/api/google_places_api.dart` when you switch to a restricted key.

Geoapify is no longer used. Gym details and workouts still come from the ASP.NET API.
