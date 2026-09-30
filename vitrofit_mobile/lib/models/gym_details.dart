/// AI-enriched (or admin-verified) details for a gym, from GymAgentService.
class GymDetails {
  final String placeId;
  final String source; // verified | ai-scraped | ai-inferred | ai-generic
  final List<String> equipment;
  final List<String> classes;
  final String? phone;
  final String? email;
  final String? openingHours;

  const GymDetails({
    required this.placeId,
    required this.source,
    required this.equipment,
    required this.classes,
    this.phone,
    this.email,
    this.openingHours,
  });

  factory GymDetails.fromJson(Map<String, dynamic> json) {
    List<String> strList(dynamic v) =>
        (v as List? ?? const []).map((e) => e.toString()).toList();
    return GymDetails(
      placeId: (json['place_id'] as String?) ?? '',
      source: (json['source'] as String?) ?? 'ai-generic',
      equipment: strList(json['equipment']),
      classes: strList(json['classes']),
      phone: json['phone'] as String?,
      email: json['email'] as String?,
      openingHours: json['opening_hours'] as String?,
    );
  }
}
