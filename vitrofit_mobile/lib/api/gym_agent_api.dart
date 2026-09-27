import 'package:dio/dio.dart';
import '../models/gym.dart';
import '../models/gym_details.dart';
import '../models/workout_suggestion.dart';

/// GymAgentService is a separate FastAPI microservice (AI-driven gym
/// enrichment/workout suggestions), not the .NET VitroFit.API - no auth.
/// Reached via `adb reverse tcp:8001 tcp:8001` on a device.
const String _defaultGymAgentBaseUrl = 'http://127.0.0.1:8001/api';
const String gymAgentBaseUrl = String.fromEnvironment('GYM_AGENT_API_URL', defaultValue: _defaultGymAgentBaseUrl);

class GymAgentException implements Exception {
  final String message;
  const GymAgentException(this.message);

  @override
  String toString() => message;
}

class GymAgentApi {
  final Dio _dio = Dio(BaseOptions(
    baseUrl: gymAgentBaseUrl,
    connectTimeout: const Duration(seconds: 10),
    receiveTimeout: const Duration(seconds: 45), // enrichment can involve an LLM call
  ));

  Future<GymDetails> getDetails(Gym gym) async {
    try {
      final response = await _dio.post('/gyms/details', data: {
        'place_id': gym.placeId,
        'name': gym.name,
        'lat': gym.lat,
        'lng': gym.lng,
        'address': gym.address,
        'website': gym.website,
        'phone': gym.phone,
        'email': gym.email,
        'opening_hours': gym.openingHours,
      });
      return GymDetails.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw GymAgentException(_messageFor(e));
    }
  }

  Future<WorkoutSuggestionsResult> getWorkoutSuggestions(GymDetails details, String gymName) async {
    try {
      final response = await _dio.post('/gyms/workouts', data: {
        'place_id': details.placeId,
        'name': gymName,
        'equipment': details.equipment,
        'classes': details.classes,
      });
      return WorkoutSuggestionsResult.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw GymAgentException(_messageFor(e));
    }
  }

  String _messageFor(DioException e) {
    if (e.type == DioExceptionType.connectionError || e.type == DioExceptionType.connectionTimeout) {
      return 'Could not reach the gym service. Check your connection and try again.';
    }
    final data = e.response?.data;
    if (data is Map && data['detail'] is String) return data['detail'] as String;
    return 'Something went wrong. Please try again.';
  }
}
