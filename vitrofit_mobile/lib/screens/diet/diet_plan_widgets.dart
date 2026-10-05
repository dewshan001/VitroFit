import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../models/diet.dart';
import '../../theme/app_theme.dart';
import '../../widgets/agent_ui.dart';
import '../../widgets/slanted_button.dart';

const Map<String, String> _riskFlagText = {
  'UNDER_18': 'under 18',
  'MEDICAL_CONDITIONS_PRESENT': 'medical condition declared',
  'BELOW_SAFE_FLOOR': 'below the 1,200 kcal safe minimum',
  'STEEP_DEFICIT': 'steep calorie deficit',
};

String riskFlagLabel(String code) => _riskFlagText[code] ?? code;

String formatDietDate(DateTime? d) {
  if (d == null) return '';
  const months = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
  ];
  final local = d.toLocal();
  return '${months[local.month - 1]} ${local.day}, ${local.year}';
}

String _n(num v) => v == v.roundToDouble() ? v.round().toString() : v.toStringAsFixed(1);

/// Numbers an agent step card needs that the bare step entry doesn't carry
/// (targets, drafted meals, overall risk).
class StepContext {
  final num? totalCalories;
  final DietMacros? macros;
  final String? riskLevel;
  final List<String> riskFlags;
  final List<DietMeal> meals;

  const StepContext({
    this.totalCalories,
    this.macros,
    this.riskLevel,
    this.riskFlags = const [],
    this.meals = const [],
  });

  factory StepContext.fromWorkflowJson(Map<String, dynamic>? d) {
    if (d == null) return const StepContext();
    final targets = d['targets'];
    return StepContext(
      totalCalories: targets is Map ? (targets['totalCalories'] as num?) : null,
      macros: targets is Map ? DietMacros.fromJson(targets['macros']) : null,
      riskLevel: d['riskLevel'] as String?,
      riskFlags: (d['riskFlags'] as List? ?? [])
          .map((f) => f is Map ? (f['code']?.toString() ?? '') : f.toString())
          .where((c) => c.isNotEmpty)
          .toList(),
      meals: (d['meals'] as List? ?? [])
          .map((e) => DietMeal.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }

  factory StepContext.fromPlan(DietPlan plan) => StepContext(
    totalCalories: plan.totalCalories,
    macros: plan.macros,
    riskLevel: plan.riskLevel,
    meals: plan.meals,
  );
}

enum _Variant { normal, pass, revise, reject }

class _StepInfo {
  final String icon;
  final String label;
  final _Variant variant;
  final List<String> points;
  const _StepInfo(this.icon, this.label, this.variant, this.points);
}

const Map<String, ({String icon, String label})> _agentMeta = {
  'NutritionAnalystAgent': (icon: '🧮', label: 'Nutrition Analyst'),
  'MealGeneratorAgent': (icon: '🧑‍🍳', label: 'Meal Generator'),
  'SafetyValidatorAgent': (icon: '🛡️', label: 'Safety Validator'),
};

String _cap(String s) => s.isEmpty ? s : '${s[0].toUpperCase()}${s.substring(1)}';

_StepInfo _describe(DietStep step, StepContext ctx, List<DietStep> all) {
  final meta = _agentMeta[step.agent] ?? (icon: '✓', label: step.agent);

  if (step.agent == 'NutritionAnalystAgent') {
    if (step.step == 1) {
      final t = ctx.totalCalories;
      final m = ctx.macros;
      return _StepInfo(meta.icon, meta.label, _Variant.normal, t != null
          ? [
              'Daily target: ${_n(t)} kcal',
              if (m != null)
                'Protein ${_n(m.protein)}g · Carbs ${_n(m.carbs)}g · Fat ${_n(m.fat)}g',
            ]
          : ['Calculating your calorie and macro targets…']);
    }
    final risk = step.riskLevel ?? ctx.riskLevel;
    final flags = step.riskFlagCodes.isNotEmpty ? step.riskFlagCodes : ctx.riskFlags;
    if (risk == null) {
      return _StepInfo(meta.icon, meta.label, _Variant.normal, ['Checking risk level…']);
    }
    final phrases = flags.map(riskFlagLabel).toList();
    return _StepInfo(
      meta.icon,
      meta.label,
      risk == 'high' ? _Variant.revise : _Variant.normal,
      [
        'Risk level: ${_cap(risk)}',
        phrases.isNotEmpty ? 'Why: ${phrases.join(', ')}' : 'No safety concerns found',
        if (risk == 'high') 'Needs Trainer/Admin approval before saving',
      ],
    );
  }

  if (step.agent == 'MealGeneratorAgent') {
    final lastGen = all.map((s) => s.agent).toList().lastIndexOf('MealGeneratorAgent');
    final isLatest = all.indexOf(step) == lastGen;
    final meals = isLatest ? ctx.meals : const <DietMeal>[];
    final names = meals.map((m) => m.label.isNotEmpty ? m.label : m.type).join(', ');
    if ((step.retry ?? 0) > 0) {
      return _StepInfo(meta.icon, meta.label, _Variant.revise, [
        meals.isNotEmpty
            ? 'Revised meals (try ${step.retry! + 1}): $names'
            : 'Revising meals (try ${step.retry! + 1})…',
      ]);
    }
    return _StepInfo(meta.icon, meta.label, _Variant.normal, [
      meals.isNotEmpty ? 'Drafted ${meals.length} meals: $names' : 'Drafting meals…',
    ]);
  }

  if (step.agent == 'SafetyValidatorAgent') {
    final reason = step.violations.map((v) => v.message).where((m) => m.isNotEmpty).take(2).join('; ');
    final other = step.violations
        .where((v) => v.code != 'CALORIE_OUT_OF_TOLERANCE')
        .map((v) => v.message)
        .where((m) => m.isNotEmpty)
        .take(2)
        .join('; ');
    final target = step.targetCalories;
    final attempt = step.attemptCalories;
    final dir = (attempt != null && target != null) ? (attempt < target ? 'under' : 'over') : null;
    final calorieLine = (target != null && target != 0)
        ? 'Total: ${attempt == null ? '?' : _n(attempt)} kcal (target ${_n(target)} kcal, ${step.diffPct == null ? '' : _n(step.diffPct!)}% ${dir ?? ''})'
        : null;

    if (step.verdict == 'pass') {
      return _StepInfo(meta.icon, meta.label, _Variant.pass,
          calorieLine != null ? [calorieLine, '✓ Within tolerance — approved'] : ['✓ Passed all checks']);
    }
    if (step.verdict == 'reject') {
      return _StepInfo(meta.icon, meta.label, _Variant.reject, [
        reason.isNotEmpty ? '✗ Rejected: $reason' : '✗ Rejected — safety issue found',
      ]);
    }
    return _StepInfo(
      meta.icon,
      meta.label,
      _Variant.revise,
      calorieLine != null
          ? [calorieLine, '⚠ Outside tolerance — revising', if (other.isNotEmpty) 'Also: $other']
          : ['⚠ Not quite on target — revising'],
    );
  }

  return _StepInfo('✓', step.agent, _Variant.normal, ['Done']);
}

/// One agent's progress card.
class AgentStepCard extends StatelessWidget {
  final DietStep step;
  final StepContext context_;
  final List<DietStep> allSteps;

  const AgentStepCard({
    super.key,
    required this.step,
    required this.context_,
    required this.allSteps,
  });

  @override
  Widget build(BuildContext context) {
    final info = _describe(step, context_, allSteps);
    final color = switch (info.variant) {
      _Variant.pass => AppColors.success,
      _Variant.reject => AppColors.error,
      _Variant.revise => AppColors.info,
      _Variant.normal => AppColors.accent,
    };
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.5)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '${info.icon}  ${info.label.toUpperCase()}',
            style: GoogleFonts.oswald(
              fontSize: 13,
              fontWeight: FontWeight.bold,
              letterSpacing: 1,
              color: color,
            ),
          ),
          const SizedBox(height: 6),
          for (final p in info.points)
            Padding(
              padding: const EdgeInsets.only(bottom: 2),
              child: Text(
                p,
                style: GoogleFonts.inter(
                  fontSize: 13,
                  height: 1.4,
                  color: AppColors.textPrimary,
                ),
              ),
            ),
        ],
      ),
    );
  }
}

/// Summary bar + meal cards, used by both a fresh result and a saved plan.
class DietPlanDetails extends StatelessWidget {
  final DietPlan plan;
  final bool hasMedicalConditions;
  final Set<String> changedKeys;

  const DietPlanDetails({
    super.key,
    required this.plan,
    required this.hasMedicalConditions,
    this.changedKeys = const {},
  });

  static const _mealIcons = {
    'breakfast': Icons.egg_alt_outlined,
    'lunch': Icons.rice_bowl_outlined,
    'dinner': Icons.dinner_dining_outlined,
    'snack': Icons.apple_outlined,
  };

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AgentBanner(
          isError: hasMedicalConditions,
          icon: Icons.medical_information_outlined,
          message:
              'This plan is generated by AI and is not medical advice.${hasMedicalConditions ? ' Given the medical condition(s) you selected, please consult a doctor or dietitian before following it.' : ' Consult a doctor or dietitian for guidance specific to your health.'}',
        ),
        if (!plan.withinTolerance) ...[
          const SizedBox(height: 10),
          const AgentBanner(
            message:
                "This plan's totals may not exactly match your calorie/macro targets. You can regenerate it, or edit the meals below before confirming.",
            icon: Icons.warning_amber_rounded,
          ),
        ],
        const SizedBox(height: 12),
        AgentCard(
          accent: true,
          child: Row(
            children: [
              _stat(_n(plan.totalCalories), 'Calories'),
              _stat('${_n(plan.macros.protein)}g', 'Protein'),
              _stat('${_n(plan.macros.carbs)}g', 'Carbs'),
              _stat('${_n(plan.macros.fat)}g', 'Fat'),
            ],
          ),
        ),
        const SizedBox(height: 12),
        for (var i = 0; i < plan.meals.length; i++) _meal(i, plan.meals[i]),
      ],
    );
  }

  Widget _stat(String value, String label) => Expanded(
    child: Column(
      children: [
        FittedBox(
          fit: BoxFit.scaleDown,
          child: Text(
            value,
            style: GoogleFonts.oswald(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              color: AppColors.accent,
            ),
          ),
        ),
        Text(
          label,
          style: GoogleFonts.inter(fontSize: 11, color: AppColors.textSecondary),
        ),
      ],
    ),
  );

  Widget _meal(int i, DietMeal meal) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: AgentCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  _mealIcons[meal.type.toLowerCase()] ?? Icons.restaurant,
                  size: 18,
                  color: AppColors.accent,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    meal.label.toUpperCase(),
                    style: GoogleFonts.oswald(
                      fontSize: 15,
                      fontWeight: FontWeight.bold,
                      color: AppColors.textPrimary,
                    ),
                  ),
                ),
                Text(
                  '${_n(meal.calories)} kcal',
                  style: GoogleFonts.inter(
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                    color: AppColors.accent,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            for (var j = 0; j < meal.items.length; j++)
              _item(meal.items[j], changedKeys.contains('$i::$j')),
          ],
        ),
      ),
    );
  }

  Widget _item(DietMealItem item, bool changed) {
    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: changed ? AppColors.accent.withValues(alpha: 0.10) : AppColors.bgSecondary,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: changed ? AppColors.borderAccent : AppColors.border,
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Flexible(
                      child: Text(
                        item.name,
                        style: GoogleFonts.inter(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: AppColors.textPrimary,
                        ),
                      ),
                    ),
                    if (changed) ...[
                      const SizedBox(width: 6),
                      Text(
                        'CHANGED',
                        style: GoogleFonts.oswald(
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                          color: AppColors.accent,
                        ),
                      ),
                    ],
                  ],
                ),
                Text(
                  item.portion,
                  style: GoogleFonts.inter(fontSize: 11.5, color: AppColors.textMuted),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '${_n(item.calories)} kcal',
                style: GoogleFonts.inter(
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                  color: AppColors.textPrimary,
                ),
              ),
              Text(
                'P ${_n(item.macros.protein)} · C ${_n(item.macros.carbs)} · F ${_n(item.macros.fat)}',
                style: GoogleFonts.inter(fontSize: 10.5, color: AppColors.textMuted),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// Free-text "edit this plan" box shown under a fresh result.
class DietRefineBox extends StatefulWidget {
  final bool applying;
  final String? message;
  final ValueChanged<String> onRefine;

  const DietRefineBox({
    super.key,
    required this.applying,
    required this.message,
    required this.onRefine,
  });

  @override
  State<DietRefineBox> createState() => _DietRefineBoxState();
}

class _DietRefineBoxState extends State<DietRefineBox> {
  final _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _submit() {
    final text = _controller.text.trim();
    if (text.isEmpty || widget.applying) return;
    widget.onRefine(text);
    _controller.clear();
  }

  @override
  Widget build(BuildContext context) {
    return AgentCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SectionTitle('Want a small change?'),
          const SizedBox(height: 8),
          AgentTextArea(
            controller: _controller,
            enabled: !widget.applying,
            hint: 'e.g. instead of rice, include something else at lunch',
            maxLength: 300,
            minLines: 1,
          ),
          SizedBox(
            width: double.infinity,
            child: SlantedButton(
              text: widget.applying ? 'APPLYING…' : 'APPLY CHANGE',
              icon: Icons.tune,
              isLoading: widget.applying,
              paddingVertical: 10,
              onPressed: _submit,
            ),
          ),
          if (widget.message != null) ...[
            const SizedBox(height: 10),
            AgentBanner(message: widget.message!, isError: true),
          ],
        ],
      ),
    );
  }
}
