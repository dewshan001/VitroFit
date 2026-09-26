import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../../api/api_exception.dart';
import '../../models/timetable_slot.dart';
import '../../models/workout.dart';
import '../../state/app_state.dart';
import '../../theme/app_theme.dart';
import '../../widgets/slanted_button.dart';
import '../../widgets/vitro_text_field.dart';

/// Opens the create/edit form for a personal timetable slot.
/// [presetWorkout] pre-selects a workout (from "Add to My Timetable").
/// [editingSlot] switches the form into edit mode for an existing slot.
Future<void> showTimetableSlotForm(
  BuildContext context, {
  Workout? presetWorkout,
  TimetableSlot? editingSlot,
}) {
  return showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (context) => _TimetableSlotForm(presetWorkout: presetWorkout, editingSlot: editingSlot),
  );
}

class _TimetableSlotForm extends StatefulWidget {
  final Workout? presetWorkout;
  final TimetableSlot? editingSlot;

  const _TimetableSlotForm({this.presetWorkout, this.editingSlot});

  @override
  State<_TimetableSlotForm> createState() => _TimetableSlotFormState();
}

class _TimetableSlotFormState extends State<_TimetableSlotForm> {
  final _formKey = GlobalKey<FormState>();
  final _titleController = TextEditingController();

  late ApiDay _day;
  late TimeOfDay _startTime;
  late TimeOfDay _endTime;
  int? _workoutId;

  bool _saving = false;
  String? _error;

  bool get _isEditing => widget.editingSlot != null;

  @override
  void initState() {
    super.initState();
    final slot = widget.editingSlot;
    if (slot != null) {
      _day = slot.day;
      _startTime = TimeOfDay(hour: slot.startTime.hour, minute: slot.startTime.minute);
      _endTime = TimeOfDay(hour: slot.endTime.hour, minute: slot.endTime.minute);
      _workoutId = slot.workoutId;
      _titleController.text = slot.title;
    } else {
      _day = ApiDay.monday;
      _startTime = const TimeOfDay(hour: 18, minute: 0);
      _endTime = const TimeOfDay(hour: 19, minute: 0);
      _workoutId = widget.presetWorkout?.id;
      _titleController.text = widget.presetWorkout?.name ?? '';
    }
  }

  @override
  void dispose() {
    _titleController.dispose();
    super.dispose();
  }

  Future<void> _pickTime({required bool isStart}) async {
    final initial = isStart ? _startTime : _endTime;
    final picked = await showTimePicker(
      context: context,
      initialTime: initial,
      builder: (context, child) => Theme(
        data: Theme.of(context).copyWith(
          colorScheme: const ColorScheme.dark(
            primary: AppColors.accent,
            onPrimary: AppColors.bgPrimary,
            surface: AppColors.bgCard,
            onSurface: AppColors.textPrimary,
          ),
        ),
        child: child!,
      ),
    );
    if (picked != null) {
      setState(() {
        if (isStart) {
          _startTime = picked;
        } else {
          _endTime = picked;
        }
      });
    }
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_workoutId == null) {
      setState(() => _error = 'Please choose a workout.');
      return;
    }
    final start = ApiTime(_startTime.hour, _startTime.minute);
    final end = ApiTime(_endTime.hour, _endTime.minute);
    if (end.totalMinutes <= start.totalMinutes) {
      setState(() => _error = 'End time must be after start time.');
      return;
    }

    setState(() {
      _saving = true;
      _error = null;
    });

    final appState = context.read<AppState>();
    try {
      if (_isEditing) {
        await appState.updateSlot(
          id: widget.editingSlot!.id,
          day: _day,
          startTime: start,
          endTime: end,
          title: _titleController.text.trim(),
          workoutId: _workoutId!,
        );
      } else {
        await appState.createSlot(
          day: _day,
          startTime: start,
          endTime: end,
          title: _titleController.text.trim(),
          workoutId: _workoutId!,
        );
      }
      if (mounted) {
        Navigator.of(context).pop();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            backgroundColor: AppColors.success,
            content: Text(
              _isEditing ? "Timetable slot updated." : "Added to your timetable!",
              style: GoogleFonts.inter(fontWeight: FontWeight.bold),
            ),
          ),
        );
      }
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } catch (_) {
      setState(() => _error = 'Something went wrong. Please try again.');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final workouts = context.watch<AppState>().workouts;

    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: Container(
        decoration: const BoxDecoration(
          color: AppColors.bgPrimary,
          borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          border: Border(top: BorderSide(color: AppColors.accent, width: 2)),
        ),
        clipBehavior: Clip.antiAlias,
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Center(
                  child: Container(
                    width: 40,
                    height: 4,
                    margin: const EdgeInsets.only(bottom: 16),
                    decoration: BoxDecoration(color: AppColors.textMuted, borderRadius: BorderRadius.circular(2)),
                  ),
                ),
                Text(
                  _isEditing ? "EDIT TIMETABLE SLOT" : "ADD TO MY TIMETABLE",
                  style: GoogleFonts.oswald(fontSize: 22, fontWeight: FontWeight.bold, color: AppColors.accent),
                ),
                const SizedBox(height: 16),
                if (_error != null)
                  Container(
                    margin: const EdgeInsets.only(bottom: 16),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppColors.errorGlow,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: AppColors.error.withOpacity(0.5)),
                    ),
                    child: Text(_error!, style: GoogleFonts.inter(color: AppColors.error, fontSize: 12.5)),
                  ),
                _fieldLabel("WORKOUT"),
                const SizedBox(height: 6),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  decoration: BoxDecoration(
                    color: AppColors.bgCard,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: AppColors.border),
                  ),
                  child: DropdownButtonHideUnderline(
                    child: DropdownButton<int>(
                      isExpanded: true,
                      value: workouts.any((w) => w.id == _workoutId) ? _workoutId : null,
                      hint: Text("Select a workout", style: GoogleFonts.inter(color: AppColors.textMuted)),
                      dropdownColor: AppColors.bgCard,
                      style: GoogleFonts.inter(color: AppColors.textPrimary),
                      icon: const Icon(Icons.arrow_drop_down, color: AppColors.accent),
                      items: workouts
                          .map((w) => DropdownMenuItem(value: w.id, child: Text("${w.name} (${w.category})")))
                          .toList(),
                      onChanged: (val) {
                        setState(() {
                          _workoutId = val;
                          if (_titleController.text.isEmpty && val != null) {
                            _titleController.text = workouts.firstWhere((w) => w.id == val).name;
                          }
                        });
                      },
                    ),
                  ),
                ),
                const SizedBox(height: 14),
                VitroTextField(
                  label: "SLOT TITLE",
                  controller: _titleController,
                  hint: "e.g. Morning session",
                  icon: Icons.edit_outlined,
                  validator: (v) => Validators.required(v, label: 'Title'),
                ),
                const SizedBox(height: 14),
                _fieldLabel("DAY"),
                const SizedBox(height: 6),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: ApiDay.weekOrder.map((d) {
                    final selected = _day == d;
                    return GestureDetector(
                      onTap: () => setState(() => _day = d),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                        decoration: BoxDecoration(
                          color: selected ? AppColors.accent : AppColors.bgCard,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: selected ? AppColors.accent : AppColors.border),
                        ),
                        child: Text(
                          d.shortLabel,
                          style: GoogleFonts.oswald(
                            fontSize: 13,
                            fontWeight: FontWeight.bold,
                            color: selected ? AppColors.bgPrimary : AppColors.textPrimary,
                          ),
                        ),
                      ),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 14),
                Row(
                  children: [
                    Expanded(child: _timeField("START TIME", _startTime, () => _pickTime(isStart: true))),
                    const SizedBox(width: 12),
                    Expanded(child: _timeField("END TIME", _endTime, () => _pickTime(isStart: false))),
                  ],
                ),
                const SizedBox(height: 24),
                SizedBox(
                  width: double.infinity,
                  child: SlantedButton(
                    text: _isEditing ? "SAVE CHANGES" : "ADD TO TIMETABLE",
                    icon: Icons.check,
                    isLoading: _saving,
                    onPressed: _submit,
                  ),
                ),
                const SizedBox(height: 8),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _fieldLabel(String label) {
    return Text(
      label,
      style: GoogleFonts.oswald(fontSize: 13, fontWeight: FontWeight.bold, letterSpacing: 1.0, color: AppColors.textPrimary),
    );
  }

  Widget _timeField(String label, TimeOfDay time, VoidCallback onTap) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _fieldLabel(label),
        const SizedBox(height: 6),
        GestureDetector(
          onTap: onTap,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
            decoration: BoxDecoration(
              color: AppColors.bgCard,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: AppColors.border),
            ),
            child: Row(
              children: [
                const Icon(Icons.access_time, size: 16, color: AppColors.accent),
                const SizedBox(width: 8),
                Text(time.format(context), style: GoogleFonts.inter(color: AppColors.textPrimary)),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
