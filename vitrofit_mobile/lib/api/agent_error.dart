import 'package:dio/dio.dart';

/// A user-presentable failure from one of the AI agent endpoints (fitness,
/// diet, time management). The backend is inconsistent about where it puts the
/// message (`message`, `detail`, `error`, `title`, or a validation `errors`
/// list), so everything is normalised here.
class AgentException implements Exception {
  final String message;
  final int? statusCode;

  /// Set for fitness `404` "profile not created yet" style responses.
  bool get isNotFound => statusCode == 404;

  const AgentException(this.message, {this.statusCode});

  factory AgentException.fromDio(DioException e, {String service = 'service'}) {
    if (e.type == DioExceptionType.connectionError ||
        e.type == DioExceptionType.connectionTimeout) {
      return const AgentException(
        'Could not reach the server. Check your connection and try again.',
      );
    }
    if (e.type == DioExceptionType.receiveTimeout ||
        e.type == DioExceptionType.sendTimeout) {
      return const AgentException(
        'The request took too long. Please try again in a moment.',
      );
    }
    final status = e.response?.statusCode;
    final fromBody = _messageFromBody(e.response?.data);
    if (fromBody != null) return AgentException(fromBody, statusCode: status);
    switch (status) {
      case 401:
        return AgentException(
          'Your session has expired. Please sign in again.',
          statusCode: status,
        );
      case 403:
        return AgentException(
          'You do not have permission to do that.',
          statusCode: status,
        );
      case 429:
        return AgentException(
          'Too many requests. Please wait a moment and try again.',
          statusCode: status,
        );
      case 503:
        return AgentException(
          'The $service is unavailable right now. Please try again later.',
          statusCode: status,
        );
      case 504:
        return AgentException(
          'The $service took too long to answer. Please try again.',
          statusCode: status,
        );
    }
    return AgentException(
      'Something went wrong. Please try again.',
      statusCode: status,
    );
  }

  static String? _messageFromBody(dynamic data) {
    if (data is! Map) return null;
    final parts = <String>[];
    for (final key in const ['message', 'detail', 'error', 'title']) {
      final v = data[key];
      if (v is String && v.trim().isNotEmpty) {
        parts.add(v.trim());
        break;
      }
    }
    final errors = data['errors'];
    if (errors is List) {
      for (final err in errors) {
        if (err is String && err.trim().isNotEmpty) parts.add(err.trim());
      }
    } else if (errors is Map) {
      for (final v in errors.values) {
        if (v is List) {
          for (final item in v) {
            if (item is String && item.trim().isNotEmpty) parts.add(item.trim());
          }
        }
      }
    }
    if (parts.isEmpty) return null;
    return parts.join('\n');
  }

  @override
  String toString() => message;
}
