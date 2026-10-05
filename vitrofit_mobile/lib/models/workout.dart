class Workout {
  final int id;
  final String name;
  final String category;
  final String? description;

  const Workout({
    required this.id,
    required this.name,
    required this.category,
    this.description,
  });

  factory Workout.fromJson(Map<String, dynamic> json) {
    return Workout(
      id: json['id'] as int,
      name: (json['name'] as String?) ?? '',
      category: (json['category'] as String?) ?? '',
      description: json['description'] as String?,
    );
  }
}
