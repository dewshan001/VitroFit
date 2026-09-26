import 'package:dio/dio.dart';
import '../models/workout.dart';
import 'api_client.dart';
import 'api_exception.dart';

class WorkoutsApi {
  final Dio _dio = ApiClient.instance.dio;

  Future<List<Workout>> list() async {
    try {
      final response = await _dio.get('/workouts');
      final data = response.data as List;
      return data.map((e) => Workout.fromJson(e as Map<String, dynamic>)).toList();
    } on DioException catch (e) {
      throw ApiException.fromDioError(e);
    }
  }
}
