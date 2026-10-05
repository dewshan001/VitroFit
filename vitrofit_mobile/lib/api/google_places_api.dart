import 'dart:math' as math;

import 'package:dio/dio.dart';
import '../models/gym.dart';
import 'api_client.dart';

/// Nearby Search (New) allows at most 50 km and 20 results per request.
const double searchRadiusMeters = 50000;
const int maxResults = 20;

class GooglePlacesException implements Exception {
  final String message;
  const GooglePlacesException(this.message);

  @override
  String toString() => message;
}

/// Great-circle distance between two points, in metres.
double haversineMeters(double lat1, double lng1, double lat2, double lng2) {
  double rad(double d) => d * math.pi / 180;
  final dLat = rad(lat2 - lat1);
  final dLng = rad(lng2 - lng1);
  final h =
      math.pow(math.sin(dLat / 2), 2) +
      math.cos(rad(lat1)) * math.cos(rad(lat2)) * math.pow(math.sin(dLng / 2), 2);
  return 2 * 6371000 * math.asin(math.sqrt(h));
}

/// Nearby gym search goes through the VitroFit API (POST /gyms/nearby), which
/// forwards to GymAgentService, where the Google Places key lives (.env), so no Places key ships in the app.
/// Only the native map SDK key (android/local.properties) remains on the device.
class GooglePlacesApi {
  GooglePlacesApi({Dio? dio}) : _dio = dio ?? ApiClient.instance.dio;

  final Dio _dio;

  /// Gyms near a point, nearest first.
  Future<List<Gym>> searchNearby({
    required double lat,
    required double lng,
  }) async {
    try {
      final response = await _dio.post(
        '/gyms/nearby',
        data: {
          'lat': lat,
          'lng': lng,
          'radiusMeters': searchRadiusMeters,
          'maxResults': maxResults,
        },
      );
      final places = (response.data['places'] as List? ?? const []);
      return places
          .map(
            (p) => Gym.fromGooglePlace(
              p as Map<String, dynamic>,
              originLat: lat,
              originLng: lng,
            ),
          )
          .whereType<Gym>()
          .toList();
    } on DioException catch (e) {
      final message = (e.response?.data is Map)
          ? (e.response!.data['detail'] as String?)
          : null;
      throw GooglePlacesException(message ?? 'Places search failed.');
    }
  }
}
