import 'package:dio/dio.dart';

import 'api_client.dart';
import 'api_exception.dart';

class AppNotification {
  final int id;
  final String type;
  final String title;
  final String message;
  final String? linkUrl;
  final bool isRead;
  final DateTime? createdAt;

  const AppNotification({
    required this.id,
    required this.type,
    required this.title,
    required this.message,
    required this.linkUrl,
    required this.isRead,
    required this.createdAt,
  });

  factory AppNotification.fromJson(Map<String, dynamic> json) {
    return AppNotification(
      id: (json['id'] as num?)?.toInt() ?? 0,
      type: (json['type'] as String?) ?? '',
      title: (json['title'] as String?) ?? '',
      message: (json['message'] as String?) ?? '',
      linkUrl: json['linkUrl'] as String?,
      isRead: json['isRead'] == true,
      createdAt: json['createdAt'] is String
          ? DateTime.tryParse(json['createdAt'] as String)
          : null,
    );
  }

  AppNotification asRead() => AppNotification(
    id: id,
    type: type,
    title: title,
    message: message,
    linkUrl: linkUrl,
    isRead: true,
    createdAt: createdAt,
  );
}

class NotificationsResult {
  final List<AppNotification> items;
  final int unreadCount;
  const NotificationsResult(this.items, this.unreadCount);
}

class NotificationsApi {
  final Dio _dio = ApiClient.instance.dio;

  Future<NotificationsResult> list() async {
    try {
      final response = await _dio.get('/notifications');
      final data = response.data as Map<String, dynamic>;
      final items = (data['items'] as List? ?? [])
          .whereType<Map<String, dynamic>>()
          .map(AppNotification.fromJson)
          .toList();
      return NotificationsResult(
        items,
        (data['unreadCount'] as num?)?.toInt() ?? 0,
      );
    } on DioException catch (e) {
      throw ApiException.fromDioError(e);
    }
  }

  Future<void> markRead(int id) async {
    try {
      await _dio.post('/notifications/$id/read');
    } on DioException catch (e) {
      throw ApiException.fromDioError(e);
    }
  }

  Future<void> markAllRead() async {
    try {
      await _dio.post('/notifications/read-all');
    } on DioException catch (e) {
      throw ApiException.fromDioError(e);
    }
  }
}
