// Models for the Fitness agent (`/api/fitness/*`), mirroring the web app's
// adaptive-fitness feature. Parsing is deliberately tolerant: the backend is
// shared with the web client and several fields are optional.

const List<String> fitnessWeekdayShort = [
  'Mon',
  'Tue',
  'Wed',
  'Thu',
  'Fri',
  'Sat',
  'Sun',
];
const List<String> fitnessWeekdayLong = [
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
  'Sunday',
];

const Map<String, String> fitnessGoals = {
  'weight_loss': 'Weight loss',
  'muscle_building': 'Build muscle',
  'general_fitness': 'General fitness',
  'strength': 'Build strength',
  'endurance': 'Improve endurance',
};

const Map<String, String> fitnessEquipment = {
  'bodyweight': 'Bodyweight',
  'dumbbells': 'Dumbbells',
  'resistance_band': 'Resistance bands',
  'gym': 'Gym access (machines, cables, barbells)',
};

const List<String> fitnessBodyAreas = [
  'chest',
  'triceps',
  'arms',
  'back',
  'legs',
  'shoulders',
  'core',
  'full body',
];

int _int(dynamic v, [int fallback = 0]) {
  if (v is int) return v;
  if (v is num) return v.toInt();
  if (v is String) return int.tryParse(v) ?? fallback;
  return fallback;
}

double _double(dynamic v, [double fallback = 0]) {
  if (v is num) return v.toDouble();
  if (v is String) return double.tryParse(v) ?? fallback;
  return fallback;
}

List<String> _strings(dynamic v) =>
    v is List ? v.map((e) => e.toString()).toList() : <String>[];

String _dateOnly(dynamic v) {
  final s = v?.toString() ?? '';
  return s.length >= 10 ? s.substring(0, 10) : s;
}

class FitnessProfile {
  final int age;
  final double heightCm;
  final double weightKg;
  final String goal;
  final List<int> days; // ISO weekdays: Monday = 1 ... Sunday = 7
  final int sessionMinutes;
  final List<String> equipment;
  final bool reviewRequired;

  const FitnessProfile({
    required this.age,
    required this.heightCm,
    required this.weightKg,
    required this.goal,
    required this.days,
    required this.sessionMinutes,
    required this.equipment,
    required this.reviewRequired,
  });

  static const FitnessProfile defaults = FitnessProfile(
    age: 25,
    heightCm: 170,
    weightKg: 70,
    goal: 'general_fitness',
    days: [1, 3, 6],
    sessionMinutes: 120,
    equipment: ['bodyweight', 'gym'],
    reviewRequired: false,
  );

  factory FitnessProfile.fromJson(Map<String, dynamic> json) {
    return FitnessProfile(
      age: _int(json['age']),
      heightCm: _double(json['heightCm']),
      weightKg: _double(json['weightKg']),
      goal: (json['goal'] as String?) ?? 'general_fitness',
      days: (json['days'] as List? ?? []).map((e) => _int(e)).toList()..sort(),
      sessionMinutes: _int(json['sessionMinutes'], 60),
      equipment: _strings(json['equipment']),
      reviewRequired: json['reviewRequired'] == true,
    );
  }

  Map<String, dynamic> toJson() => {
    'age': age,
    'heightCm': heightCm,
    'weightKg': weightKg,
    'goal': goal,
    'days': days,
    'sessionMinutes': sessionMinutes,
    'equipment': equipment,
    'reviewRequired': reviewRequired,
  };

  FitnessProfile copyWith({
    int? age,
    double? heightCm,
    double? weightKg,
    String? goal,
    List<int>? days,
    int? sessionMinutes,
    List<String>? equipment,
    bool? reviewRequired,
  }) {
    return FitnessProfile(
      age: age ?? this.age,
      heightCm: heightCm ?? this.heightCm,
      weightKg: weightKg ?? this.weightKg,
      goal: goal ?? this.goal,
      days: days ?? this.days,
      sessionMinutes: sessionMinutes ?? this.sessionMinutes,
      equipment: equipment ?? this.equipment,
      reviewRequired: reviewRequired ?? this.reviewRequired,
    );
  }
}

class FitnessExercise {
  final String id;
  final String name;
  final String muscleGroup;
  final String instructions;

  const FitnessExercise({
    required this.id,
    required this.name,
    required this.muscleGroup,
    required this.instructions,
  });

  factory FitnessExercise.fromJson(Map<String, dynamic> json) {
    return FitnessExercise(
      id: json['id'].toString(),
      name: (json['name'] as String?) ?? json['id'].toString(),
      muscleGroup: (json['muscleGroup'] as String?) ?? '',
      instructions: (json['instructions'] as String?) ?? '',
    );
  }
}

class FitnessPrescription {
  final String exerciseId;
  final int sets;
  final int repetitions;
  final int restSeconds;
  final String? adaptedFromExerciseId;
  final String? adaptationReason;

  const FitnessPrescription({
    required this.exerciseId,
    required this.sets,
    required this.repetitions,
    required this.restSeconds,
    this.adaptedFromExerciseId,
    this.adaptationReason,
  });

  factory FitnessPrescription.fromJson(Map<String, dynamic> json) {
    return FitnessPrescription(
      exerciseId: json['exerciseId'].toString(),
      sets: _int(json['sets']),
      repetitions: _int(json['repetitions']),
      restSeconds: _int(json['restSeconds']),
      adaptedFromExerciseId: json['adaptedFromExerciseId']?.toString(),
      adaptationReason: json['adaptationReason'] as String?,
    );
  }
}

class FitnessPlanDay {
  final int day; // ISO weekday, 1-7
  final String focus;
  final int warmupMinutes;
  final int cooldownMinutes;
  final int? durationMinutes;
  final List<FitnessPrescription> exercises;

  const FitnessPlanDay({
    required this.day,
    required this.focus,
    required this.warmupMinutes,
    required this.cooldownMinutes,
    required this.durationMinutes,
    required this.exercises,
  });

  factory FitnessPlanDay.fromJson(Map<String, dynamic> json) {
    return FitnessPlanDay(
      day: _int(json['day'], 1),
      focus: (json['focus'] as String?) ?? '',
      warmupMinutes: _int(json['warmupMinutes']),
      cooldownMinutes: _int(json['cooldownMinutes']),
      durationMinutes: json['durationMinutes'] == null
          ? null
          : _int(json['durationMinutes']),
      exercises: (json['exercises'] as List? ?? [])
          .map((e) => FitnessPrescription.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

class FitnessPlan {
  /// 1-4 are the beginner weeks; 5+ are three-month "workout blocks".
  final int week;
  final List<FitnessPlanDay> days;

  const FitnessPlan({required this.week, required this.days});

  bool get isBlock => week > 4;
  int get blockNumber => week - 4;
  String get title =>
      isBlock ? 'Workout block $blockNumber' : 'Beginner week $week of 4';

  factory FitnessPlan.fromJson(Map<String, dynamic> json) {
    return FitnessPlan(
      week: _int(json['week'], 1),
      days: (json['days'] as List? ?? [])
          .map((e) => FitnessPlanDay.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

class FitnessWorkflowSummary {
  final String id;
  final String status;

  const FitnessWorkflowSummary({required this.id, required this.status});

  factory FitnessWorkflowSummary.fromJson(Map<String, dynamic> json) {
    return FitnessWorkflowSummary(
      id: json['id'].toString(),
      status: (json['status'] as String?) ?? '',
    );
  }
}

class FitnessWorkflow {
  final String id;
  final String status; // Ready | Running | Failed | ReviewRequired
  final int version;
  final String? previousWorkflowId;
  final String summary;
  final String safetyNote;
  final String createdAt;
  final FitnessPlan? plan;

  const FitnessWorkflow({
    required this.id,
    required this.status,
    required this.version,
    required this.previousWorkflowId,
    required this.summary,
    required this.safetyNote,
    required this.createdAt,
    required this.plan,
  });

  bool get isReady => status == 'Ready' && plan != null;

  factory FitnessWorkflow.fromJson(Map<String, dynamic> json) {
    final plan = json['plan'];
    return FitnessWorkflow(
      id: json['id'].toString(),
      status: (json['status'] as String?) ?? '',
      version: _int(json['version']),
      previousWorkflowId: json['previousWorkflowId']?.toString(),
      summary: (json['summary'] as String?) ?? '',
      safetyNote: (json['safetyNote'] as String?) ?? '',
      createdAt: (json['createdAt'] as String?) ?? '',
      plan: plan is Map<String, dynamic> ? FitnessPlan.fromJson(plan) : null,
    );
  }
}

class FitnessProgressRecord {
  final int day;
  final bool completed;
  final int rpe;
  final bool pain;
  final List<String> affectedAreas;
  final String performedOn; // yyyy-MM-dd

  const FitnessProgressRecord({
    required this.day,
    required this.completed,
    required this.rpe,
    required this.pain,
    required this.affectedAreas,
    required this.performedOn,
  });

  /// Counts toward finishing a day (matches the web check).
  bool get countsAsRecorded => completed || pain;

  factory FitnessProgressRecord.fromJson(Map<String, dynamic> json) {
    return FitnessProgressRecord(
      day: _int(json['day'], 1),
      completed: json['completed'] == true,
      rpe: _int(json['rpe']),
      pain: json['pain'] == true,
      affectedAreas: _strings(json['affectedAreas']),
      performedOn: _dateOnly(json['performedOn']),
    );
  }
}

class FitnessEvent {
  final String step;
  final String summary;
  final int durationMs;

  const FitnessEvent({
    required this.step,
    required this.summary,
    required this.durationMs,
  });

  factory FitnessEvent.fromJson(Map<String, dynamic> json) {
    return FitnessEvent(
      step: (json['step'] as String?) ?? '',
      summary: (json['summary'] as String?) ?? '',
      durationMs: _int(json['durationMs']),
    );
  }
}

class FitnessHistory {
  final List<FitnessEvent> events;
  final List<FitnessProgressRecord> progress;

  const FitnessHistory({required this.events, required this.progress});

  factory FitnessHistory.fromJson(Map<String, dynamic> json) {
    return FitnessHistory(
      events: (json['events'] as List? ?? [])
          .map((e) => FitnessEvent.fromJson(e as Map<String, dynamic>))
          .toList(),
      progress: (json['progress'] as List? ?? [])
          .map((e) => FitnessProgressRecord.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

/// The saved three-month cycle (`next-cycle`); only the end date is needed to
/// decide whether a fresh review is due.
class FitnessCycle {
  final String? endDate; // yyyy-MM-dd

  const FitnessCycle({this.endDate});

  factory FitnessCycle.fromJson(Map<String, dynamic> json) {
    final end = json['endDate'];
    return FitnessCycle(endDate: end == null ? null : _dateOnly(end));
  }
}

/// Answers to the three-month check-in form (`POST next-cycle`).
class CycleReviewInput {
  final String painOrDiscomfort;
  final String injuriesOrRestrictions;
  final String currentCondition;
  final String goal;
  final int availableWorkoutMinutes;
  final List<int> availableDays;
  final List<String> equipment;

  const CycleReviewInput({
    required this.painOrDiscomfort,
    required this.injuriesOrRestrictions,
    required this.currentCondition,
    required this.goal,
    required this.availableWorkoutMinutes,
    required this.availableDays,
    required this.equipment,
  });

  Map<String, dynamic> toJson() => {
    'painOrDiscomfort': painOrDiscomfort,
    'injuriesOrRestrictions': injuriesOrRestrictions,
    'currentCondition': currentCondition,
    'goal': goal,
    'availableWorkoutMinutes': availableWorkoutMinutes,
    'availableDays': availableDays,
    'equipment': equipment,
  };
}

/// One recorded session (`PUT progress`).
class ProgressInput {
  final int day;
  final int rpe;
  final bool completed;
  final bool pain;
  final List<String> affectedAreas;
  final String performedOn; // yyyy-MM-dd

  const ProgressInput({
    required this.day,
    required this.rpe,
    required this.completed,
    required this.pain,
    required this.affectedAreas,
    required this.performedOn,
  });

  Map<String, dynamic> toJson() => {
    'day': day,
    'rpe': rpe,
    'completed': completed,
    'pain': pain,
    'affectedAreas': pain ? affectedAreas : <String>[],
    'performedOn': performedOn,
  };
}
