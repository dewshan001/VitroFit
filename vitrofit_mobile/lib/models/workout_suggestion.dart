class WorkoutSuggestion {
  final String name;
  final String category;
  final int durationMinutes;
  final String difficulty;
  final String description;
  final List<String> equipmentUsed;

  const WorkoutSuggestion({
    required this.name,
    required this.category,
    required this.durationMinutes,
    required this.difficulty,
    required this.description,
    required this.equipmentUsed,
  });

  factory WorkoutSuggestion.fromJson(Map<String, dynamic> json) {
    return WorkoutSuggestion(
      name: (json['name'] as String?) ?? 'Suggested workout',
      category: (json['category'] as String?) ?? 'General',
      durationMinutes: (json['duration_minutes'] as num?)?.toInt() ?? 30,
      difficulty: (json['difficulty'] as String?) ?? 'All levels',
      description: (json['description'] as String?) ?? '',
      equipmentUsed: (json['equipment_used'] as List? ?? const []).map((e) => e.toString()).toList(),
    );
  }
}

class WorkoutSuggestionsResult {
  final List<WorkoutSuggestion> workouts;
  final String? notes;

  const WorkoutSuggestionsResult({required this.workouts, this.notes});

  factory WorkoutSuggestionsResult.fromJson(Map<String, dynamic> json) {
    final list = (json['workouts'] as List? ?? const [])
        .map((e) => WorkoutSuggestion.fromJson(e as Map<String, dynamic>))
        .toList();
    final notes = json['notes'] as String?;
    return WorkoutSuggestionsResult(workouts: list, notes: (notes != null && notes.isNotEmpty) ? notes : null);
  }
}
