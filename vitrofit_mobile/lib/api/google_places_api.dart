import 'dart:math' as math;

import 'package:dio/dio.dart';
import '../models/gym.dart';

/// Browser/app Google key for Places (New), passed at build time:
///   flutter run --dart-define=GOOGLE_MAPS_API_KEY=...
/// It ships inside the app, so restrict it in Google Cloud (Android package +
/// SHA-1, Places API (New) only). The native map key is separate and lives in
/// android/local.properties (see README).
const String _googleMapsApiKey = String.fromEnvironment('GOOGLE_MAPS_API_KEY');

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

class GooglePlacesApi {
  GooglePlacesApi({Dio? dio})
    : _dio =
          dio ??
          Dio(
            BaseOptions(
              baseUrl: 'https://places.googleapis.com',
              connectTimeout: const Duration(seconds: 12),
              receiveTimeout: const Duration(seconds: 12),
            ),
          );

  final Dio _dio;

  static const _fieldMask =
      'places.id,places.displayName,places.formattedAddress,places.location,'
      'places.websiteUri,places.nationalPhoneNumber';

  /// Gyms near a point, nearest first.
  Future<List<Gym>> searchNearby({
    required double lat,
    required double lng,
  }) async {
    if (_googleMapsApiKey.isEmpty) {
      throw const GooglePlacesException(
        'Google Maps key is not set. Run with --dart-define=GOOGLE_MAPS_API_KEY=...',
      );
    }
    try {
      final response = await _dio.post(
        '/v1/places:searchNearby',
        options: Options(
          headers: {
            'X-Goog-Api-Key': _googleMapsApiKey,
            'X-Goog-FieldMask': _fieldMask,
          },
        ),
        data: {
          'includedTypes': ['gym'],
          'languageCode': 'en',
          'maxResultCount': maxResults,
          'rankPreference': 'DISTANCE',
          'locationRestriction': {
            'circle': {
              'center': {'latitude': lat, 'longitude': lng},
              'radius': searchRadiusMeters,
            },
          },
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
          ? (e.response!.data['error']?['message'] as String?)
          : null;
      throw GooglePlacesException(message ?? 'Places search failed.');
    }
  }
}
