import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../models/fitness.dart';
import '../../theme/app_theme.dart';
import '../../widgets/agent_ui.dart';
import '../../widgets/slanted_button.dart';
import '../../widgets/vitro_text_field.dart';

/// Three-month check-in shown when a cycle is complete (mirrors CycleReviewForm).
class FitnessCycleReviewForm extends StatefulWidget {
  final FitnessProfile? profile;
  final bool busy;
  final Future<void> Function(CycleReviewInput review) onSubmit;

  const FitnessCycleReviewForm({
    super.key,
    required this.profile,
    required this.busy,
    required this.onSubmit,
  });

  @override
  State<FitnessCycleReviewForm> createState() => _FitnessCycleReviewFormState();
}

class _FitnessCycleReviewFormState extends State<FitnessCycleReviewForm> {
  final _formKey = GlobalKey<FormState>();
  final _pain = TextEditingController(text: 'No current pain or discomfort');
  final _injuries = TextEditingController(
    text: 'No current injuries or exercise restrictions',
  );
  final _condition = TextEditingController();
  late final TextEditingController _minutes;
  late String _goal;
  late List<int> _days;
  late List<String> _equipment;

  @override
  void initState() {
    super.initState();
    final p = widget.profile;
    _goal = fitnessGoals.containsKey(p?.goal) ? p!.goal : 'general_fitness';
    _minutes = TextEditingController(
      text: (p?.sessionMinutes ?? 120).clamp(100, 120).toString(),
    );
    final days = p?.days ?? const [1, 3, 5];
    _days = [...days];
    _equipment = (p?.equipment.isNotEmpty ?? false)
        ? [...p!.equipment]
        : ['bodyweight'];
  }

  @override
  void dispose() {
    _pain.dispose();
    _injuries.dispose();
    _condition.dispose();
    _minutes.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_days.length < 3 || _days.length > 4 || _equipment.isEmpty) return;
    await widget.onSubmit(
      CycleReviewInput(
        painOrDiscomfort: _pain.text.trim(),
        injuriesOrRestrictions: _injuries.text.trim(),
        currentCondition: _condition.text.trim(),
        goal: _goal,
        availableWorkoutMinutes: int.parse(_minutes.text.trim()),
        availableDays: [..._days]..sort(),
        equipment: _equipment,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AgentCard(
      accent: true,
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SectionTitle('Review your current condition'),
            const SizedBox(height: 6),
            Text(
              'These answers guide the next 3-month schedule. If you have significant, worsening, or persistent pain, seek qualified professional guidance before training.',
              style: GoogleFonts.inter(
                fontSize: 12.5,
                height: 1.4,
                color: AppColors.textSecondary,
              ),
            ),
            const SizedBox(height: 14),
            const FieldLabel('Pain or discomfort'),
            _area(_pain, 300, required: true),
            const SizedBox(height: 10),
            const FieldLabel('Injuries or exercise restrictions'),
            _area(_injuries, 300, required: true),
            const SizedBox(height: 10),
            const FieldLabel('How are you feeling now?'),
            _area(
              _condition,
              500,
              required: true,
              hint: 'Describe your current condition.',
            ),
            const SizedBox(height: 10),
            const FieldLabel('Current goal'),
            AgentDropdown<String>(
              value: _goal,
              items: fitnessGoals.entries
                  .map((e) => DropdownMenuItem(value: e.key, child: Text(e.value)))
                  .toList(),
              onChanged: (v) => setState(() => _goal = v ?? _goal),
            ),
            const SizedBox(height: 12),
            VitroTextField(
              label: 'WORKOUT MINUTES (100–120)',
              controller: _minutes,
              hint: '100–120',
              icon: Icons.timer_outlined,
              keyboardType: TextInputType.number,
              validator: (v) {
                final n = int.tryParse((v ?? '').trim());
                if (n == null || n < 100 || n > 120) {
                  return 'Enter between 100 and 120 minutes.';
                }
                return null;
              },
            ),
            const SizedBox(height: 12),
            const FieldLabel('Available workout days (choose 3 or 4)'),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: List.generate(7, (i) {
                final day = i + 1;
                final selected = _days.contains(day);
                final locked =
                    (!selected && _days.length >= 4) ||
                    (selected && _days.length <= 3);
                return SelectChip(
                  label: fitnessWeekdayShort[i].toUpperCase(),
                  selected: selected,
                  onTap: locked
                      ? null
                      : () => setState(
                          () => selected ? _days.remove(day) : _days.add(day),
                        ),
                );
              }),
            ),
            const SizedBox(height: 12),
            const FieldLabel('Available equipment'),
            for (final entry in fitnessEquipment.entries)
              CheckRow(
                label: entry.value,
                value: _equipment.contains(entry.key),
                onChanged: (v) => setState(
                  () => v ? _equipment.add(entry.key) : _equipment.remove(entry.key),
                ),
              ),
            const SizedBox(height: 14),
            SizedBox(
              width: double.infinity,
              child: SlantedButton(
                text: 'SAVE REVIEW & GENERATE NEXT 3-MONTH SCHEDULE',
                icon: Icons.check,
                isLoading: widget.busy,
                isDisabled: _equipment.isEmpty,
                onPressed: _submit,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _area(
    TextEditingController c,
    int maxLength, {
    bool required = false,
    String hint = '',
  }) {
    return TextFormField(
      controller: c,
      minLines: 2,
      maxLines: 4,
      maxLength: maxLength,
      validator: required
          ? (v) => (v == null || v.trim().length < 2) ? 'Please fill this in.' : null
          : null,
      style: GoogleFonts.inter(color: AppColors.textPrimary, fontSize: 14),
      decoration: InputDecoration(
        hintText: hint,
        hintStyle: GoogleFonts.inter(color: AppColors.textMuted, fontSize: 13),
        filled: true,
        fillColor: AppColors.bgCard,
        counterStyle: GoogleFonts.inter(color: AppColors.textMuted, fontSize: 10),
        errorStyle: GoogleFonts.inter(color: AppColors.error, fontSize: 11),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: AppColors.border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: AppColors.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: AppColors.accent, width: 1.5),
        ),
      ),
    );
  }
}
