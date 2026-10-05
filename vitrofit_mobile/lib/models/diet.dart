// Models for the Diet agent (`/api/diet/*`), mirroring the web app's
// diet-plan feature. The API is a pass-through to the Python DietPlanService.

class DietOption {
  final String value;
  final String label;
  final String? sub;
  const DietOption(this.value, this.label, [this.sub]);
}

const List<DietOption> dietActivityOptions = [
  DietOption('sedentary', 'Sedentary (little exercise)'),
  DietOption('light', 'Lightly active (1–3 days / week)'),
  DietOption('moderate', 'Moderately active (3–5 days / week)'),
  DietOption('active', 'Very active (6–7 days / week)'),
];

const List<DietOption> dietGenderOptions = [
  DietOption('male', 'Male'),
  DietOption('female', 'Female'),
  DietOption('other', 'Other'),
];

const List<DietOption> dietGoalOptions = [
  DietOption('weight loss', 'Weight Loss'),
  DietOption('muscle gain', 'Muscle Gain'),
  DietOption('maintenance', 'Maintenance'),
  DietOption('endurance', 'Endurance'),
];

const List<String> dietRestrictions = [
  'vegetarian',
  'vegan',
  'halal',
  'dairy-free',
  'gluten-free',
  'peanut allergy',
  'lactose-intolerant',
];

const List<DietOption> dietMealFrequencies = [
  DietOption('3Meals', '3 meals / day'),
  DietOption('4Meals', '4 meals / day'),
  DietOption('5Meals', '5 meals / day'),
  DietOption('intermittent', 'Intermittent fasting (16:8)'),
];

const int dietBudgetMin = 500;
const int dietBudgetMax = 15000;

const List<DietOption> dietBudgetTiers = [
  DietOption('low', 'Low', 'Below Rs.2,000/day'),
  DietOption('medium', 'Medium', 'Rs.2,000 – 4,000/day'),
  DietOption('high', 'High', 'Above Rs.4,000/day'),
  DietOption('custom', 'Custom', 'Set your own (Rs.500 – 15,000/day)'),
];

const List<String> dietMedicalConditions = [
  'diabetes',
  'high blood pressure',
  'high cholesterol',
  'heart condition',
  'kidney condition',
  'thyroid condition',
];

const List<DietOption> dietCookingTimes = [
  DietOption('quick', 'Quick meals only (< 15 min)'),
  DietOption('moderate', "Moderate, I don't mind some prep"),
  DietOption('nocook', 'No-cook / ready-to-eat only'),
];

num _num(dynamic v, [num fallback = 0]) {
  if (v is num) return v;
  if (v is String) return num.tryParse(v) ?? fallback;
  return fallback;
}

List<String> _strings(dynamic v) =>
    v is List ? v.map((e) => e.toString()).toList() : <String>[];

/// The preferences form / `inputs` of a plan (`DietPlanPreferences`).
class DietPrefs {
  final int age;
  final String gender;
  final num heightCm;
  final num weightKg;
  final String activityLevel;
  final String goal;
  final String mealFrequency;
  final List<String> restrictions;
  final String dislikes;
  final String budgetTier;
  final int? budgetCustomAmount;
  final List<String> medicalConditions;
  final String cookingTime;

  const DietPrefs({
    required this.age,
    required this.gender,
    required this.heightCm,
    required this.weightKg,
    required this.activityLevel,
    required this.goal,
    required this.mealFrequency,
    required this.restrictions,
    required this.dislikes,
    required this.budgetTier,
    required this.budgetCustomAmount,
    required this.medicalConditions,
    required this.cookingTime,
  });

  static const DietPrefs defaults = DietPrefs(
    age: 25,
    gender: 'male',
    heightCm: 175,
    weightKg: 70,
    activityLevel: 'moderate',
    goal: 'maintenance',
    mealFrequency: '3Meals',
    restrictions: [],
    dislikes: '',
    budgetTier: 'medium',
    budgetCustomAmount: null,
    medicalConditions: [],
    cookingTime: 'moderate',
  );

  factory DietPrefs.fromJson(Map<String, dynamic>? json) {
    if (json == null) return defaults;
    final custom = json['budgetCustomAmount'];
    return DietPrefs(
      age: _num(json['age'], defaults.age).toInt(),
      gender: (json['gender'] as String?) ?? defaults.gender,
      heightCm: _num(json['heightCm'], defaults.heightCm),
      weightKg: _num(json['weightKg'], defaults.weightKg),
      activityLevel:
          (json['activityLevel'] as String?) ?? defaults.activityLevel,
      goal: (json['goal'] as String?) ?? defaults.goal,
      mealFrequency:
          (json['mealFrequency'] as String?) ?? defaults.mealFrequency,
      restrictions: _strings(json['restrictions']),
      dislikes: (json['dislikes'] as String?) ?? '',
      budgetTier: (json['budgetTier'] as String?) ?? defaults.budgetTier,
      budgetCustomAmount: custom == null ? null : _num(custom).toInt(),
      medicalConditions: _strings(json['medicalConditions']),
      cookingTime: (json['cookingTime'] as String?) ?? defaults.cookingTime,
    );
  }

  Map<String, dynamic> toJson() => {
    'age': age,
    'gender': gender,
    'heightCm': heightCm,
    'weightKg': weightKg,
    'activityLevel': activityLevel,
    'goal': goal,
    'mealFrequency': mealFrequency,
    'restrictions': restrictions,
    'dislikes': dislikes,
    'budgetTier': budgetTier,
    'budgetCustomAmount': budgetTier == 'custom' ? budgetCustomAmount : null,
    'medicalConditions': medicalConditions,
    'cookingTime': cookingTime,
  };
}

class DietMacros {
  final num protein;
  final num carbs;
  final num fat;
  const DietMacros({this.protein = 0, this.carbs = 0, this.fat = 0});

  factory DietMacros.fromJson(dynamic json) {
    if (json is! Map) return const DietMacros();
    return DietMacros(
      protein: _num(json['protein']),
      carbs: _num(json['carbs']),
      fat: _num(json['fat']),
    );
  }
}

class DietMealItem {
  final String name;
  final String portion;
  final num calories;
  final DietMacros macros;
  const DietMealItem({
    required this.name,
    required this.portion,
    required this.calories,
    required this.macros,
  });

  factory DietMealItem.fromJson(Map<String, dynamic> json) => DietMealItem(
    name: (json['name'] as String?) ?? '',
    portion: (json['portion'] as String?) ?? '',
    calories: _num(json['calories']),
    macros: DietMacros.fromJson(json['macros']),
  );
}

class DietMeal {
  final String type;
  final String label;
  final List<DietMealItem> items;
  const DietMeal({
    required this.type,
    required this.label,
    required this.items,
  });

  num get calories => items.fold<num>(0, (sum, i) => sum + i.calories);

  factory DietMeal.fromJson(Map<String, dynamic> json) => DietMeal(
    type: (json['type'] as String?) ?? '',
    label: (json['label'] as String?) ?? (json['type'] as String?) ?? '',
    items: (json['items'] as List? ?? [])
        .map((e) => DietMealItem.fromJson(e as Map<String, dynamic>))
        .toList(),
  );
}

/// One entry of a workflow's `completedSteps` (an agent's progress card).
class DietStep {
  final String agent;
  final int? step;
  final List<String> riskFlagCodes;
  final String? riskLevel;
  final String? verdict;
  final List<({String code, String message})> violations;
  final num? attemptCalories;
  final num? targetCalories;
  final num? diffPct;
  final int? retry;
  final int? attempt;
  final bool refine;

  const DietStep({
    required this.agent,
    this.step,
    this.riskFlagCodes = const [],
    this.riskLevel,
    this.verdict,
    this.violations = const [],
    this.attemptCalories,
    this.targetCalories,
    this.diffPct,
    this.retry,
    this.attempt,
    this.refine = false,
  });

  factory DietStep.fromJson(Map<String, dynamic> json) {
    num? opt(dynamic v) => v == null ? null : _num(v);
    return DietStep(
      agent: (json['agent'] as String?) ?? '',
      step: opt(json['step'])?.toInt(),
      riskFlagCodes: (json['riskFlags'] as List? ?? [])
          .map((f) => f is Map ? (f['code']?.toString() ?? '') : f.toString())
          .where((c) => c.isNotEmpty)
          .toList(),
      riskLevel: json['riskLevel'] as String?,
      verdict: json['verdict'] as String?,
      violations: (json['violations'] as List? ?? [])
          .whereType<Map>()
          .map(
            (v) => (
              code: v['code']?.toString() ?? '',
              message: v['message']?.toString() ?? '',
            ),
          )
          .toList(),
      attemptCalories: opt(json['attemptCalories']),
      targetCalories: opt(json['targetCalories']),
      diffPct: opt(json['diffPct']),
      retry: opt(json['retry'])?.toInt(),
      attempt: opt(json['attempt'])?.toInt(),
      refine: json['refine'] == true || json['refine'] is num && json['refine'] != 0,
    );
  }
}

/// A generated or saved plan. [rawMeals] keeps the server's meal JSON verbatim
/// so confirming/saving sends back exactly what was generated.
class DietPlan {
  final num totalCalories;
  final DietMacros macros;
  final List<DietMeal> meals;
  final List<dynamic> rawMeals;
  final bool withinTolerance;
  final String? workflowId;
  final String? riskLevel;
  final List<DietStep> steps;
  final bool requiresApproval;
  final String? note;

  /// Saved-plan fields.
  final int? id;
  final DateTime? createdAt;
  final String approvalStatus;
  final DietPrefs? inputs;

  const DietPlan({
    required this.totalCalories,
    required this.macros,
    required this.meals,
    required this.rawMeals,
    required this.withinTolerance,
    this.workflowId,
    this.riskLevel,
    this.steps = const [],
    this.requiresApproval = false,
    this.note,
    this.id,
    this.createdAt,
    this.approvalStatus = 'approved',
    this.inputs,
  });

  bool get isPending => approvalStatus == 'pending';

  /// From a completed `GET workflows/{id}` response.
  factory DietPlan.fromWorkflow(Map<String, dynamic> d) {
    final targets = d['targets'] as Map<String, dynamic>?;
    final rawMeals = (d['meals'] as List?) ?? const [];
    final outcome = d['finalOutcome'];
    return DietPlan(
      totalCalories: _num(targets?['totalCalories']),
      macros: DietMacros.fromJson(targets?['macros']),
      meals: rawMeals
          .map((e) => DietMeal.fromJson(e as Map<String, dynamic>))
          .toList(),
      rawMeals: rawMeals,
      withinTolerance: outcome is Map ? outcome['withinTolerance'] != false : true,
      workflowId: d['id']?.toString(),
      riskLevel: d['riskLevel'] as String?,
      steps: (d['completedSteps'] as List? ?? [])
          .map((e) => DietStep.fromJson(e as Map<String, dynamic>))
          .toList(),
      requiresApproval: d['approvalStatus'] == 'pending',
      note: d['message'] as String?,
      inputs: d['inputs'] is Map<String, dynamic>
          ? DietPrefs.fromJson(d['inputs'] as Map<String, dynamic>)
          : null,
    );
  }

  /// From an item of `GET plans`. Pending items have no content yet.
  factory DietPlan.fromSaved(Map<String, dynamic> d) {
    final rawMeals = (d['meals'] as List?) ?? const [];
    return DietPlan(
      id: _num(d['id']).toInt(),
      createdAt: DateTime.tryParse(d['createdAt']?.toString() ?? ''),
      approvalStatus: (d['approvalStatus'] as String?) ?? 'approved',
      totalCalories: _num(d['totalCalories']),
      macros: DietMacros.fromJson(d['macros']),
      meals: rawMeals
          .map((e) => DietMeal.fromJson(e as Map<String, dynamic>))
          .toList(),
      rawMeals: rawMeals,
      withinTolerance: d['withinTolerance'] != false,
      workflowId: d['workflowId']?.toString(),
      inputs: d['inputs'] is Map<String, dynamic>
          ? DietPrefs.fromJson(d['inputs'] as Map<String, dynamic>)
          : null,
    );
  }

  /// Body for `POST confirm` / `PUT plans/{id}`.
  Map<String, dynamic> toSaveJson(DietPrefs prefs) => {
    'inputs': prefs.toJson(),
    'totalCalories': totalCalories,
    'macros': {
      'protein': macros.protein,
      'carbs': macros.carbs,
      'fat': macros.fat,
    },
    'meals': rawMeals,
    'withinTolerance': withinTolerance,
    'workflowId': workflowId,
  };
}

/// The state of a polled workflow while it is still being generated.
class DietWorkflowStatus {
  final String status; // running | completed | failed | rejected
  final String? message;
  final List<DietStep> steps;
  final Map<String, dynamic> raw;

  const DietWorkflowStatus({
    required this.status,
    required this.message,
    required this.steps,
    required this.raw,
  });

  bool get isTerminal =>
      status == 'completed' || status == 'failed' || status == 'rejected';

  factory DietWorkflowStatus.fromJson(Map<String, dynamic> d) =>
      DietWorkflowStatus(
        status: (d['status'] as String?) ?? 'running',
        message: d['message'] as String?,
        steps: (d['completedSteps'] as List? ?? [])
            .map((e) => DietStep.fromJson(e as Map<String, dynamic>))
            .toList(),
        raw: d,
      );
}

/// A high-risk plan waiting for a Trainer/Admin decision.
class DietApprovalItem {
  final String workflowId;
  final String userId;
  final String riskLevel;
  final List<String> riskFlags;
  final num totalCalories;
  final DateTime? createdAt;

  const DietApprovalItem({
    required this.workflowId,
    required this.userId,
    required this.riskLevel,
    required this.riskFlags,
    required this.totalCalories,
    required this.createdAt,
  });

  factory DietApprovalItem.fromJson(Map<String, dynamic> d) => DietApprovalItem(
    workflowId: (d['workflowId'] ?? d['id']).toString(),
    userId: (d['userId'] ?? '').toString(),
    riskLevel: (d['riskLevel'] as String?) ?? '',
    riskFlags: (d['riskFlags'] as List? ?? [])
        .map((f) => f is Map ? (f['code']?.toString() ?? '') : f.toString())
        .where((c) => c.isNotEmpty)
        .toList(),
    totalCalories: _num(d['totalCalories']),
    createdAt: DateTime.tryParse(d['createdAt']?.toString() ?? ''),
  );
}
