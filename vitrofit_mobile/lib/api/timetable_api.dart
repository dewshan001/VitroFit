import 'package:dio/dio.dart';
import '../models/timetable_slot.dart';
import 'api_client.dart';
import 'api_exception.dart';

class TimetableApi {
  final Dio _dio = ApiClient.instance.dio;

  Future<List<TimetableSlot>> list() async {
    try {
      final response = await _dio.get('/timetable');
      final data = response.data as List;
      return data.map((e) => TimetableSlot.fromJson(e as Map<String, dynamic>)).toList();
    } on DioException catch (e) {
      throw ApiException.fromDioError(e);
    }
  }

  Future<TimetableSlot> create({
    required ApiDay day,
    required ApiTime startTime,
    required ApiTime endTime,
    required String title,
    required int workoutId,
  }) async {
    try {
      final response = await _dio.post('/timetable', data: {
        'day': day.netValue,
        'startTime': startTime.toApiString(),
        'endTime': endTime.toApiString(),
        'title': title,
        'workoutId': workoutId,
      });
      return TimetableSlot.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiException.fromDioError(e);
    }
  }

  Future<TimetableSlot> update({
    required int id,
    required ApiDay day,
    required ApiTime startTime,
    required ApiTime endTime,
    required String title,
    required int workoutId,
  }) async {
    try {
      final response = await _dio.put('/timetable/$id', data: {
        'day': day.netValue,
        'startTime': startTime.toApiString(),
        'endTime': endTime.toApiString(),
        'title': title,
        'workoutId': workoutId,
      });
      return TimetableSlot.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiException.fromDioError(e);
    }
  }

  Future<void> delete(int id) async {
    try {
      await _dio.delete('/timetable/$id');
    } on DioException catch (e) {
      throw ApiException.fromDioError(e);
    }
  }
}
