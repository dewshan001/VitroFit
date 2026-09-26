import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

/// A normalized error surfaced from the backend, extracted from either the
/// `{error}` or `{message}` response shapes the API uses inconsistently,
/// with a fallback for network failures and unparsable/empty error bodies.
class ApiException implements Exception {
  final String message;
  final int? statusCode;

  const ApiException(this.message, {this.statusCode});

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
        return ApiException(msg, statusCode: response.statusCode);
      }
    }
    if (error.type == DioExceptionType.connectionError ||
        error.type == DioExceptionType.connectionTimeout) {
      return const ApiException('Could not reach the server. Check your connection and try again.');
    }
    if (response != null) {
      return ApiException('Server error (${response.statusCode}). Please try again.', statusCode: response.statusCode);
    }
    return const ApiException('Something went wrong. Please try again.');
  }

  @override
  String toString() => message;
}
