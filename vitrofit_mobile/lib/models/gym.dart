/// A nearby gym returned by the Geoapify Places API (GeoJSON feature).
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

  factory Gym.fromFeature(Map<String, dynamic> feature) {
    final props = (feature['properties'] as Map?)?.cast<String, dynamic>() ?? {};
    final geometry = (feature['geometry'] as Map?)?.cast<String, dynamic>() ?? {};
    final coords = (geometry['coordinates'] as List?) ?? const [0.0, 0.0];
    final raw = (((props['datasource'] as Map?)?['raw'] as Map?))?.cast<String, dynamic>() ?? {};

    String? str(dynamic v) => v is String && v.isNotEmpty ? v : null;

    return Gym(
      placeId: (props['place_id'] as String?) ?? '',
      name: (props['name'] as String?) ?? 'Unnamed gym',
      lat: (coords[1] as num).toDouble(),
      lng: (coords[0] as num).toDouble(),
      address: str(props['formatted']) ?? str(props['address_line1']),
      distanceMeters: (props['distance'] as num?)?.toDouble(),
      website: str(props['website']) ?? str(raw['website']),
      phone: str(raw['phone']) ?? str(raw['contact:phone']),
      email: str(raw['email']) ?? str(raw['contact:email']),
      openingHours: str(raw['opening_hours']),
    );
  }

  double get distanceKm => (distanceMeters ?? 0) / 1000;
}
