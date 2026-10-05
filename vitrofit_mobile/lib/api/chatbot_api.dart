import 'dart:convert';

import 'package:dio/dio.dart';

import '../config/app_config.dart';

/// The chatbot is reached through the main VitroFit API's `POST /api/chat`
/// proxy (same as the deployed web app), so the app only needs the one
/// backend URL from [AppConfig].

class ChatbotException implements Exception {
  final String message;
  const ChatbotException(this.message);

  @override
  String toString() => message;
}

class ChatbotApi {
  final Dio _dio = Dio(
    BaseOptions(
      baseUrl: AppConfig.apiBaseUrl,
      connectTimeout: const Duration(seconds: 12),
      receiveTimeout: const Duration(minutes: 2),
    ),
  );

  /// Streams incremental text chunks for a single stateless turn, matching
  /// the website's SSE contract: lines of `data: {"content": "..."}`,
  /// ending with `data: [DONE]` or `data: {"error": "..."}`.
  Stream<String> sendMessage(String query) async* {
    Response<ResponseBody> response;
    try {
      response = await _dio.post<ResponseBody>(
        '/chat',
        data: {'query': query},
        options: Options(
          responseType: ResponseType.stream,
          headers: {'Accept': 'text/event-stream'},
        ),
      );
    } on DioException catch (e) {
      throw ChatbotException(await _messageForDioError(e));
    }

    final stream = response.data!.stream;
    var buffer = '';

    await for (final chunk in stream) {
      buffer += utf8.decode(chunk, allowMalformed: true);
      final events = buffer.split('\n\n');
      buffer = events.removeLast();

      for (final event in events) {
        final dataLine = event
            .split('\n')
            .firstWhere((l) => l.startsWith('data: '), orElse: () => '');
        if (dataLine.isEmpty) continue;

        final payload = dataLine.substring(6).trim();
        if (payload == '[DONE]') continue;

        Map<String, dynamic> parsed;
        try {
          parsed = jsonDecode(payload) as Map<String, dynamic>;
        } catch (_) {
          continue;
        }

        if (parsed['error'] is String) {
          throw ChatbotException(parsed['error'] as String);
        }
        final content = parsed['content'];
        if (content is String && content.isNotEmpty) {
          yield content;
        }
      }
    }
  }

  Future<String> _messageForDioError(DioException e) async {
    if (e.type == DioExceptionType.connectionError ||
        e.type == DioExceptionType.connectionTimeout) {
      return 'Could not reach VitroBot. Check your connection and try again.';
    }
    final data = e.response?.data;
    if (data is ResponseBody) {
      try {
        final bytes = await data.stream.fold<List<int>>(
          [],
          (acc, chunk) => acc..addAll(chunk),
        );
        final decoded = jsonDecode(utf8.decode(bytes)) as Map<String, dynamic>;
        final detail = decoded['detail'];
        if (detail is String && detail.isNotEmpty) return detail;
      } catch (_) {}
    }
    return 'Something went wrong. Please try again.';
  }
}
