import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

/// A normalized error surfaced from the backend, extracted from either the
/// `{error}` or `{message}` response shapes the API uses inconsistently,
/// with a fallback for network failures and unparsable/empty error bodies.
class ApiException implements Exception {
  final String message;
  final int? statusCode;

  /// Machine-readable code some endpoints return (e.g. login's
  /// `GYM_PENDING` / `GYM_REJECTED` for gym owners whose application isn't
  /// approved) and the reviewer's note that may accompany it.
  final String? code;
  final String? note;

  /// Individual validation problems from `{error, errors: [...]}` responses.
  final List<String> details;

  const ApiException(
    this.message, {
    this.statusCode,
    this.code,
    this.note,
    this.details = const [],
  });

  factory ApiException.fromDioError(DioException error) {
    if (kDebugMode) {
      // Surfaces the real Dio failure in the run terminal / logcat, since the
      // messages below are deliberately generic for the UI. Connection
      // failures in particular collapse many distinct causes (wrong host,
      // firewall, server down) into one banner - this line is what actually
      // tells you which one you're looking at.
      debugPrint(
        '[ApiException] type=${error.type} message=${error.message} '
        'underlying=${error.error} url=${error.requestOptions.uri}',
      );
    }
    final response = error.response;
    if (response?.data is Map) {
      final data = response!.data as Map;
      final msg = data['error'] ?? data['message'];
      if (msg is String && msg.trim().isNotEmpty) {
        final rawErrors = data['errors'];
        return ApiException(
          msg,
          statusCode: response.statusCode,
          code: data['code'] is String ? data['code'] as String : null,
          note: data['note'] is String ? data['note'] as String : null,
          details: rawErrors is List
              ? rawErrors.whereType<String>().toList()
              : const [],
        );
      }
    }
    if (error.type == DioExceptionType.connectionError ||
        error.type == DioExceptionType.connectionTimeout) {
      return const ApiException(
        'Could not reach the server. Check your connection and try again.',
      );
    }
    if (response?.statusCode == 429) {
      return const ApiException(
        'Too many attempts from this connection. Please try again later.',
        statusCode: 429,
      );
    }
    if (response?.statusCode == 413) {
      return const ApiException(
        'The files are too large. Please use smaller files.',
        statusCode: 413,
      );
    }
    if (response != null) {
      return ApiException(
        'Server error (${response.statusCode}). Please try again.',
        statusCode: response.statusCode,
      );
    }
    return const ApiException('Something went wrong. Please try again.');
  }

  @override
  String toString() => message;
}
