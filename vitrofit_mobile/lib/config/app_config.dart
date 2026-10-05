/// The ONE place the app's backend address is configured.
///
/// The mobile app talks only to the deployed VitroFit .NET API (the same one
/// the web app uses). Every other service (chatbot, gym agent, time agent...)
/// is reached through that API.
///
/// Hosted / APK build: replace the placeholder below with your deployed URL
/// (must end in /api, e.g. https://your-app.onrender.com/api), or pass it at
/// build time without editing this file:
///   flutter build apk --release --dart-define=API_BASE_URL=https://your-app.onrender.com/api
///
/// Local testing (debug builds allow plain http):
///   flutter run --dart-define=API_BASE_URL=http://10.0.2.2:5284/api      (Android emulator)
///   flutter run --dart-define=API_BASE_URL=http://PC-LAN-IP:5284/api   (phone on same Wi-Fi)
class AppConfig {
  AppConfig._();

  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://REPLACE-WITH-DEPLOYED-BACKEND/api',
  );
}
