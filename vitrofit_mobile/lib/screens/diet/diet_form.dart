import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../models/diet.dart';
import '../../theme/app_theme.dart';
import '../../widgets/agent_ui.dart';
import '../../widgets/slanted_button.dart';
import '../../widgets/vitro_text_field.dart';

/// Diet preferences form (mirrors the web DietPlanPreferenceForm).
class DietForm extends StatefulWidget {
  final DietPrefs initial;
  final ValueChanged<DietPrefs> onSubmit;
  final VoidCallback? onCancel;

  const DietForm({
    super.key,
    required this.initial,
    required this.onSubmit,
    this.onCancel,
  });

  @override
  State<DietForm> createState() => _DietFormState();
}

class _DietFormState extends State<DietForm> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _age;
  late final TextEditingController _height;
  late final TextEditingController _weight;
  late final TextEditingController _budget;
  late final TextEditingController _dislikes;

  late String _gender;
  late String _activity;
  late String _goal;
  late String _budgetTier;
  late String _mealFrequency;
  late String _cookingTime;
  late List<String> _restrictions;
  late List<String> _conditions;

  @override
  void initState() {
    super.initState();
    final p = widget.initial;
    String t(num v) => v == v.roundToDouble() ? v.round().toString() : v.toString();
    _age = TextEditingController(text: t(p.age));
    _height = TextEditingController(text: t(p.heightCm));
    _weight = TextEditingController(text: t(p.weightKg));
    _budget = TextEditingController(text: p.budgetCustomAmount?.toString() ?? '');
    _dislikes = TextEditingController(text: p.dislikes);
    _gender = p.gender;
    _activity = p.activityLevel;
    _goal = p.goal;
    _budgetTier = p.budgetTier;
    _mealFrequency = p.mealFrequency;
    _cookingTime = p.cookingTime;
    _restrictions = [...p.restrictions];
    _conditions = [...p.medicalConditions];
  }

  @override
  void dispose() {
    _age.dispose();
    _height.dispose();
    _weight.dispose();
    _budget.dispose();
    _dislikes.dispose();
    super.dispose();
  }

  String? _range(String? v, num min, num max, String label) {
    final n = num.tryParse((v ?? '').trim());
    if (n == null) return '$label is required.';
    if (n < min || n > max) return 'Enter $label between $min and $max.';
    return null;
  }

  void _submit() {
    if (!_formKey.currentState!.validate()) return;
    widget.onSubmit(
      DietPrefs(
        age: int.parse(_age.text.trim()),
        gender: _gender,
        heightCm: num.parse(_height.text.trim()),
        weightKg: num.parse(_weight.text.trim()),
        activityLevel: _activity,
        goal: _goal,
        mealFrequency: _mealFrequency,
        restrictions: _restrictions,
        dislikes: _dislikes.text.trim(),
        budgetTier: _budgetTier,
        budgetCustomAmount: _budgetTier == 'custom'
            ? int.parse(_budget.text.trim())
            : null,
        medicalConditions: _conditions,
        cookingTime: _cookingTime,
      ),
    );
  }

  Widget _single(List<DietOption> options, String value, ValueChanged<String> set) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        for (final o in options)
          SelectChip(
            label: o.label,
            sub: o.sub,
            selected: value == o.value,
            onTap: () => setState(() => set(o.value)),
          ),
      ],
    );
  }

  Widget _multi(List<String> options, List<String> selected) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        for (final o in options)
          SelectChip(
            label: o,
            selected: selected.contains(o),
            onTap: () => setState(
              () => selected.contains(o) ? selected.remove(o) : selected.add(o),
            ),
          ),
      ],
    );
  }

  Widget _group(String title, Widget child, {String? hint}) => Padding(
    padding: const EdgeInsets.only(bottom: 18),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SectionTitle(title),
        const SizedBox(height: 8),
        child,
        if (hint != null)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Text(
              hint,
              style: GoogleFonts.inter(fontSize: 11.5, color: AppColors.textMuted, height: 1.4),
            ),
          ),
      ],
    ),
  );

  @override
  Widget build(BuildContext context) {
    return AgentCard(
      accent: true,
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Tell us about you',
              style: GoogleFonts.oswald(
                fontSize: 22,
                fontWeight: FontWeight.bold,
                color: AppColors.textPrimary,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'All fields help tailor your plan.',
              style: GoogleFonts.inter(fontSize: 12.5, color: AppColors.textSecondary),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: VitroTextField(
                    label: 'AGE',
                    controller: _age,
                    hint: '10–100',
                    icon: Icons.cake_outlined,
                    keyboardType: TextInputType.number,
                    validator: (v) => _range(v, 10, 100, 'an age'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const FieldLabel('Gender'),
                      AgentDropdown<String>(
                        value: _gender,
                        items: [
                          for (final o in dietGenderOptions)
                            DropdownMenuItem(value: o.value, child: Text(o.label)),
                        ],
                        onChanged: (v) => setState(() => _gender = v ?? _gender),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: VitroTextField(
                    label: 'HEIGHT (CM)',
                    controller: _height,
                    hint: '100–260',
                    icon: Icons.height,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    validator: (v) => _range(v, 100, 260, 'a height'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: VitroTextField(
                    label: 'WEIGHT (KG)',
                    controller: _weight,
                    hint: '30–250',
                    icon: Icons.monitor_weight_outlined,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    validator: (v) => _range(v, 30, 250, 'a weight'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            const FieldLabel('Activity level'),
            AgentDropdown<String>(
              value: _activity,
              items: [
                for (final o in dietActivityOptions)
                  DropdownMenuItem(value: o.value, child: Text(o.label)),
              ],
              onChanged: (v) => setState(() => _activity = v ?? _activity),
            ),
            const SizedBox(height: 18),
            _group('Your primary goal', _single(dietGoalOptions, _goal, (v) => _goal = v)),
            _group(
              'Food budget',
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _single(dietBudgetTiers, _budgetTier, (v) => _budgetTier = v),
                  if (_budgetTier == 'custom') ...[
                    const SizedBox(height: 10),
                    VitroTextField(
                      label: 'DAILY BUDGET (RS.)',
                      controller: _budget,
                      hint: '$dietBudgetMin–$dietBudgetMax',
                      icon: Icons.payments_outlined,
                      keyboardType: TextInputType.number,
                      validator: (v) {
                        final n = int.tryParse((v ?? '').trim());
                        if (n == null || n < dietBudgetMin || n > dietBudgetMax) {
                          return 'Enter an amount between Rs.$dietBudgetMin and Rs.$dietBudgetMax.';
                        }
                        return null;
                      },
                    ),
                  ],
                ],
              ),
            ),
            _group(
              'Dietary preferences',
              _multi(dietRestrictions, _restrictions),
              hint: 'Select any that apply (optional).',
            ),
            _group(
              'Meal frequency',
              _single(dietMealFrequencies, _mealFrequency, (v) => _mealFrequency = v),
            ),
            _group(
              'Medical conditions',
              _multi(dietMedicalConditions, _conditions),
              hint:
                  'Select any that apply, if any (optional). This is not medical advice — always confirm your plan with a doctor or dietitian if you have a medical condition.',
            ),
            _group(
              'Cooking time / skill',
              _single(dietCookingTimes, _cookingTime, (v) => _cookingTime = v),
            ),
            _group(
              'Anything we should avoid?',
              AgentTextArea(
                controller: _dislikes,
                hint: "e.g. I don't like mushrooms or cinnamon, prefer mild spice levels…",
                maxLength: 300,
                minLines: 2,
              ),
            ),
            SizedBox(
              width: double.infinity,
              child: SlantedButton(
                text: 'GENERATE MY PLAN',
                icon: Icons.auto_awesome,
                onPressed: _submit,
              ),
            ),
            if (widget.onCancel != null)
              Center(
                child: AgentTextButton(
                  label: 'Cancel',
                  icon: Icons.close,
                  onPressed: widget.onCancel,
                ),
              ),
          ],
        ),
      ),
    );
  }
}
