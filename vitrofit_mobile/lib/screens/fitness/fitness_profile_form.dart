import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../models/fitness.dart';
import '../../theme/app_theme.dart';
import '../../widgets/agent_ui.dart';
import '../../widgets/slanted_button.dart';
import '../../widgets/vitro_text_field.dart';

/// Create / edit the fitness profile (mirrors the web FitnessProfileForm).
class FitnessProfileForm extends StatefulWidget {
  final FitnessProfile? initial;
  final bool busy;

  /// True when saving should also generate the first schedule.
  final bool createSchedule;
  final VoidCallback? onCancel;
  final Future<void> Function(FitnessProfile profile) onSave;

  const FitnessProfileForm({
    super.key,
    required this.initial,
    required this.busy,
    required this.createSchedule,
    required this.onSave,
    this.onCancel,
  });

  @override
  State<FitnessProfileForm> createState() => _FitnessProfileFormState();
}

class _FitnessProfileFormState extends State<FitnessProfileForm> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _age;
  late final TextEditingController _height;
  late final TextEditingController _weight;
  late final TextEditingController _minutes;
  late String _goal;
  late List<int> _days;
  late List<String> _equipment;
  late bool _reviewRequired;

  bool _healthClear = false;
  bool _confirmed = false;

  @override
  void initState() {
    super.initState();
    final p = widget.initial ?? FitnessProfile.defaults;
    _age = TextEditingController(text: p.age.toString());
    _height = TextEditingController(text: _trim(p.heightCm));
    _weight = TextEditingController(text: _trim(p.weightKg));
    _minutes = TextEditingController(text: p.sessionMinutes.toString());
    _goal = fitnessGoals.containsKey(p.goal) ? p.goal : 'general_fitness';
    _days = [...p.days];
    _equipment = [...p.equipment];
    _reviewRequired = p.reviewRequired;
  }

  @override
  void dispose() {
    _age.dispose();
    _height.dispose();
    _weight.dispose();
    _minutes.dispose();
    super.dispose();
  }

  static String _trim(double v) =>
      v == v.roundToDouble() ? v.round().toString() : v.toString();

  bool get _canSave =>
      _healthClear || (widget.initial?.reviewRequired == true && _reviewRequired);

  String? _range(String? v, num min, num max, String label) {
    final n = num.tryParse((v ?? '').trim());
    if (n == null) return '$label is required.';
    if (n < min || n > max) return '$label must be between $min and $max.';
    return null;
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_days.length < 3 || _days.length > 4) return;
    if (_equipment.isEmpty) return;
    await widget.onSave(
      FitnessProfile(
        age: int.parse(_age.text.trim()),
        heightCm: double.parse(_height.text.trim()),
        weightKg: double.parse(_weight.text.trim()),
        goal: _goal,
        days: [..._days]..sort(),
        sessionMinutes: int.parse(_minutes.text.trim()),
        equipment: _equipment,
        reviewRequired: _reviewRequired,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final label = widget.createSchedule && !_reviewRequired
        ? 'SAVE PROFILE & CREATE FIRST SCHEDULE'
        : _reviewRequired
        ? 'SAVE PROFILE — PAUSE SELF-SCHEDULING'
        : 'SAVE PROFILE';
    final ready =
        _canSave && _confirmed && _days.length >= 3 && _equipment.isNotEmpty;

    return AgentCard(
      accent: true,
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'START WITH THE ESSENTIALS',
              style: GoogleFonts.oswald(
                fontSize: 11,
                letterSpacing: 2,
                fontWeight: FontWeight.bold,
                color: AppColors.accent,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'Your beginner fitness profile',
              style: GoogleFonts.oswald(
                fontSize: 22,
                fontWeight: FontWeight.bold,
                color: AppColors.textPrimary,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'For adult beginners. Plans are built around the equipment you choose.',
              style: GoogleFonts.inter(
                fontSize: 12.5,
                color: AppColors.textSecondary,
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: VitroTextField(
                    label: 'AGE',
                    controller: _age,
                    hint: '18–80',
                    icon: Icons.cake_outlined,
                    keyboardType: TextInputType.number,
                    validator: (v) => _range(v, 18, 80, 'Age'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: VitroTextField(
                    label: 'MINUTES',
                    controller: _minutes,
                    hint: '20–120',
                    icon: Icons.timer_outlined,
                    keyboardType: TextInputType.number,
                    validator: (v) => _range(v, 20, 120, 'Minutes'),
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
                    hint: '100–250',
                    icon: Icons.height,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    validator: (v) => _range(v, 100, 250, 'Height'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: VitroTextField(
                    label: 'WEIGHT (KG)',
                    controller: _weight,
                    hint: '30–300',
                    icon: Icons.monitor_weight_outlined,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    validator: (v) => _range(v, 30, 300, 'Weight'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            const FieldLabel('Your training target'),
            AgentDropdown<String>(
              value: _goal,
              items: fitnessGoals.entries
                  .map((e) => DropdownMenuItem(value: e.key, child: Text(e.value)))
                  .toList(),
              onChanged: (v) => setState(() => _goal = v ?? _goal),
            ),
            const SizedBox(height: 14),
            FieldLabel('Available training days (choose 3 or 4)'),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: List.generate(7, (i) {
                final day = i + 1;
                final selected = _days.contains(day);
                final locked =
                    (!selected && _days.length >= 4) ||
                    (selected && _days.length <= 3);
                return Opacity(
                  opacity: locked && !selected ? 0.4 : 1,
                  child: SelectChip(
                    label: fitnessWeekdayShort[i].toUpperCase(),
                    selected: selected,
                    onTap: locked
                        ? null
                        : () => setState(
                            () => selected ? _days.remove(day) : _days.add(day),
                          ),
                  ),
                );
              }),
            ),
            const SizedBox(height: 14),
            const FieldLabel('Available equipment'),
            for (final entry in fitnessEquipment.entries)
              CheckRow(
                label: entry.value,
                value: _equipment.contains(entry.key),
                onChanged: (v) => setState(
                  () => v ? _equipment.add(entry.key) : _equipment.remove(entry.key),
                ),
              ),
            if (_equipment.isEmpty)
              Text(
                'Choose at least one type of equipment.',
                style: GoogleFonts.inter(fontSize: 11, color: AppColors.error),
              ),
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.bgSecondary,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: AppColors.border),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SectionTitle('Self-training health check'),
                  const SizedBox(height: 6),
                  Text(
                    'Do any of these apply: chest discomfort, fainting, or unusual breathlessness during activity; a medical condition not cleared or controlled for exercise; recent surgery or injury; pregnancy-related exercise restrictions; or a clinician advised you to avoid exercise or seek guidance?',
                    style: GoogleFonts.inter(
                      fontSize: 12,
                      height: 1.4,
                      color: AppColors.textSecondary,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'If any concern applies to you, do not confirm below and do not start a self-guided plan. Speak with an instructor or qualified health professional first.',
                    style: GoogleFonts.inter(
                      fontSize: 12,
                      height: 1.4,
                      color: AppColors.textMuted,
                    ),
                  ),
                  const SizedBox(height: 8),
                  CheckRow(
                    label:
                        'None of these concerns apply to me. I want to create a self-guided beginner plan.',
                    value: _healthClear,
                    onChanged: (v) => setState(() {
                      _healthClear = v;
                      if (widget.initial?.reviewRequired == true) {
                        _reviewRequired = !v;
                      }
                    }),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 10),
            CheckRow(
              label:
                  'I confirm my profile information is accurate and understand a beginner schedule is not medical clearance.',
              value: _confirmed,
              onChanged: (v) => setState(() => _confirmed = v),
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: SlantedButton(
                text: label,
                icon: Icons.check,
                isLoading: widget.busy,
                isDisabled: !ready,
                onPressed: _submit,
              ),
            ),
            if (!_canSave)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  'Tick the health check above to enable saving.',
                  style: GoogleFonts.inter(fontSize: 11.5, color: AppColors.textMuted),
                ),
              ),
            if (widget.onCancel != null)
              Center(
                child: AgentTextButton(
                  label: 'Cancel',
                  icon: Icons.close,
                  onPressed: widget.busy ? null : widget.onCancel,
                ),
              ),
          ],
        ),
      ),
    );
  }
}
