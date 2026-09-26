import 'package:dio/dio.dart';
import '../services/token_storage.dart';

/// Defaults to the emulator's own loopback address, reached via
/// `adb reverse tcp:5284 tcp:5284` (run this once per emulator boot/restart
/// so 127.0.0.1:5284 inside the emulator tunnels straight to the backend on
/// the host). This is more reliable than the classic 10.0.2.2 NAT alias,
/// which depends on the emulator's SLIRP networking correctly proxying TCP
/// (in practice this has been flaky on some Windows + AVD combinations even
/// when ICMP to 10.0.2.2 works fine).
///
/// Override at build/run time for a physical device, iOS simulator, or if
/// you'd rather use 10.0.2.2 directly, e.g.:
///   flutter run --dart-define=API_BASE_URL=http://192.168.1.20:5284/api
///   flutter run --dart-define=API_BASE_URL=http://10.0.2.2:5284/api
const String _defaultBaseUrl = 'http://127.0.0.1:5284/api';
const String apiBaseUrl = String.fromEnvironment('API_BASE_URL', defaultValue: _defaultBaseUrl);

/// Central Dio client: attaches the bearer token to every request and, on a
/// 401, attempts exactly one silent refresh-and-retry before giving up.
class ApiClient {
  ApiClient._() {
    _dio = Dio(BaseOptions(
      baseUrl: apiBaseUrl,
      connectTimeout: const Duration(seconds: 12),
      receiveTimeout: const Duration(seconds: 12),
    ));

    _refreshDio = Dio(BaseOptions(
      baseUrl: apiBaseUrl,
      connectTimeout: const Duration(seconds: 12),
    ));

    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        if (options.extra['skipAuth'] != true) {
          final token = await TokenStorage.instance.accessToken;
          if (token != null) {
            options.headers['Authorization'] = 'Bearer $token';
          }
        }
        handler.next(options);
      },
      onError: (error, handler) async {
        final isUnauthorized = error.response?.statusCode == 401;
        final alreadyRetried = error.requestOptions.extra['retried'] == true;
        final isAuthEndpoint = error.requestOptions.path.contains('/auth/login') ||
            error.requestOptions.path.contains('/auth/refresh') ||
            error.requestOptions.path.contains('/auth/register');

        if (!isUnauthorized || alreadyRetried || isAuthEndpoint) {
          handler.next(error);
          return;
        }

        final refreshed = await _tryRefresh();
        if (!refreshed) {
          onSessionExpired?.call();
          handler.next(error);
          return;
        }

        try {
          final retryOptions = error.requestOptions;
          retryOptions.extra['retried'] = true;
          final newToken = await TokenStorage.instance.accessToken;
          if (newToken != null) {
            retryOptions.headers['Authorization'] = 'Bearer $newToken';
          }
          final response = await _dio.fetch(retryOptions);
          handler.resolve(response);
        } on DioException catch (retryError) {
          handler.next(retryError);
        }
      },
    ));
  }

  static final ApiClient instance = ApiClient._();

  late final Dio _dio;
  late final Dio _refreshDio;

  Dio get dio => _dio;

  /// Set by AppState so a failed refresh can force a client-side logout.
  void Function()? onSessionExpired;

  Future<bool>? _refreshInFlight;

  Future<bool> _tryRefresh() {
    // Coalesce concurrent 401s into a single refresh attempt.
    return _refreshInFlight ??= _doRefresh().whenComplete(() => _refreshInFlight = null);
  }

  Future<bool> _doRefresh() async {
    final refreshToken = await TokenStorage.instance.refreshToken;
    if (refreshToken == null) return false;

    try {
      final response = await _refreshDio.post('/auth/refresh', data: {'token': refreshToken});
      final data = response.data as Map<String, dynamic>;
      final newAccessToken = data['accessToken'] as String?;
      final newRefreshToken = data['refreshToken'] as String?;
      if (newAccessToken == null || newRefreshToken == null) return false;
      await TokenStorage.instance.save(accessToken: newAccessToken, refreshToken: newRefreshToken);
      return true;
    } catch (_) {
      return false;
    }
  }
}
