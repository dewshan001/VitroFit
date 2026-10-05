import '../api/google_places_api.dart' show haversineMeters;

/// A nearby gym returned by the Google Places API (New).
class Gym {
  final String placeId;
  final String name;
  final double lat;
  final double lng;
  final String? address;
  final double? distanceMeters;
  final String? website;
  final String? phone;
  final String? email;
  final String? openingHours;

  const Gym({
    required this.placeId,
    required this.name,
    required this.lat,
    required this.lng,
    this.address,
    this.distanceMeters,
    this.website,
    this.phone,
    this.email,
    this.openingHours,
  });

  /// From a Places API (New) place. Returns null when the place has no id or
  /// location. [originLat]/[originLng] is the search centre, used for the
  /// distance (the API does not return one).
  static Gym? fromGooglePlace(
    Map<String, dynamic> place, {
    double? originLat,
    double? originLng,
  }) {
    final id = place['id'];
    final location = (place['location'] as Map?)?.cast<String, dynamic>();
    final lat = (location?['latitude'] as num?)?.toDouble();
    final lng = (location?['longitude'] as num?)?.toDouble();
    if (id is! String || id.isEmpty || lat == null || lng == null) return null;

    String? str(dynamic v) => v is String && v.isNotEmpty ? v : null;

    return Gym(
      placeId: id,
      name: str((place['displayName'] as Map?)?['text']) ?? 'Unnamed gym',
      lat: lat,
      lng: lng,
      address: str(place['formattedAddress']),
      distanceMeters: (originLat != null && originLng != null)
          ? haversineMeters(originLat, originLng, lat, lng).roundToDouble()
          : null,
      website: str(place['websiteUri']),
      phone: str(place['nationalPhoneNumber']),
    );
  }

  double get distanceKm => (distanceMeters ?? 0) / 1000;
}
