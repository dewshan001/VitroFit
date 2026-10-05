import 'package:dio/dio.dart';
import '../config/app_config.dart';
import '../services/token_storage.dart';

/// Backend base URL - see [AppConfig] for how to point it at a local or
/// hosted backend.
const String apiBaseUrl = AppConfig.apiBaseUrl;

/// Central Dio client: attaches the bearer token to every request and, on a
/// 401, attempts exactly one silent refresh-and-retry before giving up.
class ApiClient {
  ApiClient._() {
    _dio = Dio(
      BaseOptions(
        baseUrl: apiBaseUrl,
        connectTimeout: const Duration(seconds: 12),
        receiveTimeout: const Duration(seconds: 12),
      ),
    );

    _refreshDio = Dio(
      BaseOptions(
        baseUrl: apiBaseUrl,
        connectTimeout: const Duration(seconds: 12),
      ),
    );

    _dio.interceptors.add(
      InterceptorsWrapper(
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
          final isAuthEndpoint =
              error.requestOptions.path.contains('/auth/login') ||
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
      ),
    );
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
    return _refreshInFlight ??= _doRefresh().whenComplete(
      () => _refreshInFlight = null,
    );
  }

  Future<bool> _doRefresh() async {
    final refreshToken = await TokenStorage.instance.refreshToken;
    if (refreshToken == null) return false;

    try {
      final response = await _refreshDio.post(
        '/auth/refresh',
        data: {'token': refreshToken},
      );
      final data = response.data as Map<String, dynamic>;
      final newAccessToken = data['accessToken'] as String?;
      final newRefreshToken = data['refreshToken'] as String?;
      if (newAccessToken == null || newRefreshToken == null) return false;
      await TokenStorage.instance.save(
        accessToken: newAccessToken,
        refreshToken: newRefreshToken,
      );
      return true;
    } catch (_) {
      return false;
    }
  }
}
