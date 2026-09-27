import 'package:dio/dio.dart';
import '../models/gym.dart';

/// Same public client-side key the website ships in its bundle - Geoapify
/// keys are designed to be used directly from browsers/apps, not proxied.
const String _geoapifyApiKey = String.fromEnvironment(
  'GEOAPIFY_API_KEY',
  defaultValue: 'df0e01be60a848199b726c73604f3280',
);

class GeoapifyApi {
  final Dio _dio = Dio(BaseOptions(
    baseUrl: 'https://api.geoapify.com',
    connectTimeout: const Duration(seconds: 12),
    receiveTimeout: const Duration(seconds: 12),
  ));

  /// Mirrors the website's query exactly: fitness places within 50km,
  /// biased/sorted by distance from the given point.
  Future<List<Gym>> searchNearby({required double lat, required double lng}) async {
    final response = await _dio.get('/v2/places', queryParameters: {
      'categories': 'sport.fitness',
      'filter': 'circle:$lng,$lat,50000',
      'bias': 'proximity:$lng,$lat',
      'limit': 80,
      'apiKey': _geoapifyApiKey,
    });
    final features = (response.data['features'] as List? ?? const []);
    return features.map((f) => Gym.fromFeature(f as Map<String, dynamic>)).toList();
  }
}
