import 'package:dio/dio.dart';
import 'api_client.dart';
import '../models/gym.dart';
import '../models/gym_details.dart';
import '../models/workout_suggestion.dart';

/// Gym details and workout suggestions go through the VitroFit API
/// (POST /gyms/details, /gyms/workouts) with the signed-in user's token; the
/// AI service behind it is internal and is never called from the app.

class GymAgentException implements Exception {
  final String message;
  const GymAgentException(this.message);

  @override
  String toString() => message;
}

class GymAgentApi {
  GymAgentApi({Dio? dio}) : _dio = dio ?? ApiClient.instance.dio;

  final Dio _dio;

  // Enrichment can involve an LLM call, so allow far longer than the shared
  // client's default read timeout.
  static final _aiOptions = Options(receiveTimeout: const Duration(seconds: 60));

  Future<GymDetails> getDetails(Gym gym) async {
    try {
      final response = await _dio.post(
        '/gyms/details',
        options: _aiOptions,
        data: {
          'placeId': gym.placeId,
          'name': gym.name,
          'lat': gym.lat,
          'lng': gym.lng,
          'address': gym.address,
          'website': gym.website,
          'phone': gym.phone,
          'email': gym.email,
          'openingHours': gym.openingHours,
        },
      );
      return GymDetails.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw GymAgentException(_messageFor(e));
    }
  }

  Future<WorkoutSuggestionsResult> getWorkoutSuggestions(
    GymDetails details,
    String gymName,
  ) async {
    try {
      final response = await _dio.post(
        '/gyms/workouts',
        options: _aiOptions,
        data: {
          'placeId': details.placeId,
          'name': gymName,
          'equipment': details.equipment,
          'classes': details.classes,
        },
      );
      return WorkoutSuggestionsResult.fromJson(
        response.data as Map<String, dynamic>,
      );
    } on DioException catch (e) {
      throw GymAgentException(_messageFor(e));
    }
  }

  String _messageFor(DioException e) {
    if (e.type == DioExceptionType.connectionError ||
        e.type == DioExceptionType.connectionTimeout) {
      return 'Could not reach the server. Check your connection and try again.';
    }
    switch (e.response?.statusCode) {
      case 401:
        return 'Your session has expired. Please sign in again.';
      case 429:
        return 'Too many requests. Please wait a moment and try again.';
      case 503:
        return 'The gym service is unavailable right now. Please try again later.';
      case 504:
        return 'The gym service took too long to answer. Please try again.';
    }
    final data = e.response?.data;
    if (data is Map) {
      final message = data['detail'] ?? data['title'];
      if (message is String) return message;
    }
    return 'Something went wrong. Please try again.';
  }
}
