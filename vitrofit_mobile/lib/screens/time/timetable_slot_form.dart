import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../../api/api_exception.dart';
import '../../api/workouts_api.dart';
import '../../models/timetable_slot.dart';
import '../../models/workout.dart';
import '../../state/app_state.dart';
import '../../theme/app_theme.dart';
import '../../widgets/liquid_glass.dart';
import '../../widgets/slanted_button.dart';
import '../../widgets/vitro_text_field.dart';

/// Opens the create/edit form for a timetable slot (used to adjust a generated
/// timetable by hand).
/// [presetDay] pre-selects a day when creating.
/// [editingSlot] switches the form into edit mode for an existing slot.
Future<void> showTimetableSlotForm(
  BuildContext context, {
  ApiDay? presetDay,
  TimetableSlot? editingSlot,
}) {
  return showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (context) => _TimetableSlotForm(
      presetDay: presetDay,
      editingSlot: editingSlot,
    ),
  );
}

/// Shared "REMOVE SLOT?" confirmation dialog used by both the timetable list
/// (swipe-to-delete) and the edit form's Delete button.
Future<bool> confirmRemoveTimetableSlot(
  BuildContext context,
  String title,
) async {
  final confirmed = await showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      backgroundColor: AppColors.bgCard,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: const BorderSide(color: AppColors.error),
      ),
      title: Text(
        "REMOVE SLOT?",
        style: GoogleFonts.oswald(
          fontWeight: FontWeight.bold,
          color: AppColors.error,
        ),
      ),
      content: Text(
        "Remove \"$title\" from your timetable?",
        style: GoogleFonts.inter(color: AppColors.textSecondary),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context, false),
          child: Text(
            "CANCEL",
            style: GoogleFonts.oswald(color: AppColors.textMuted),
          ),
        ),
        TextButton(
          onPressed: () => Navigator.pop(context, true),
          child: Text(
            "REMOVE",
            style: GoogleFonts.oswald(
              color: AppColors.error,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
      ],
    ),
  );
  return confirmed == true;
}

class _TimetableSlotForm extends StatefulWidget {
  final ApiDay? presetDay;
  final TimetableSlot? editingSlot;

  const _TimetableSlotForm({this.presetDay, this.editingSlot});

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

  List<Workout> _workouts = [];
  bool _workoutsLoading = true;
  String? _workoutsError;

  bool _saving = false;
  bool _deleting = false;
  String? _error;

  bool get _isEditing => widget.editingSlot != null;

  @override
  void initState() {
    super.initState();
    // The workout list backs the dropdown (generated slots reference the
    // "Adaptive" workouts the server created for the timetable).
    _loadWorkouts();

    final slot = widget.editingSlot;
    if (slot != null) {
      _day = slot.day;
      _startTime = TimeOfDay(
        hour: slot.startTime.hour,
        minute: slot.startTime.minute,
      );
      _endTime = TimeOfDay(
        hour: slot.endTime.hour,
        minute: slot.endTime.minute,
      );
      _workoutId = slot.workoutId;
      _titleController.text = slot.title;
    } else {
      _day = widget.presetDay ?? ApiDay.monday;
      _startTime = const TimeOfDay(hour: 18, minute: 0);
      _endTime = const TimeOfDay(hour: 19, minute: 0);
    }
  }

  Future<void> _loadWorkouts() async {
    try {
      final list = await WorkoutsApi().list();
      if (!mounted) return;
      setState(() {
        _workouts = list;
        _workoutsLoading = false;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _workoutsError = e.message;
        _workoutsLoading = false;
      });
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
              _isEditing
                  ? "Timetable slot updated."
                  : "Session added to your timetable!",
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

  Future<void> _delete() async {
    final slot = widget.editingSlot;
    if (slot == null) return;
    final confirmed = await confirmRemoveTimetableSlot(context, slot.title);
    if (!confirmed || !mounted) return;

    setState(() => _deleting = true);
    try {
      await context.read<AppState>().deleteSlot(slot.id);
      if (mounted) {
        Navigator.of(context).pop();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            backgroundColor: AppColors.bgCard,
            content: Text("Slot removed.", style: GoogleFonts.inter()),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _deleting = false;
          _error = e is ApiException
              ? e.message
              : 'Could not remove this slot. Please try again.';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final workouts = _workouts;

    return Padding(
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
      ),
      child: LiquidGlassContainer(
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        tint: AppColors.bgPrimary,
        tintOpacity: 0.75,
        blur: false,
        border: const Border(
          top: BorderSide(color: AppColors.accent, width: 2),
        ),
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
                    decoration: BoxDecoration(
                      color: AppColors.textMuted,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ),
                Text(
                  _isEditing ? "EDIT TIMETABLE SLOT" : "ADD A SESSION",
                  style: GoogleFonts.oswald(
                    fontSize: 22,
                    fontWeight: FontWeight.bold,
                    color: AppColors.accent,
                  ),
                ),
                const SizedBox(height: 16),
                if (_error != null)
                  Container(
                    margin: const EdgeInsets.only(bottom: 16),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppColors.errorGlow,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(
                        color: AppColors.error.withValues(alpha: 0.5),
                      ),
                    ),
                    child: Text(
                      _error!,
                      style: GoogleFonts.inter(
                        color: AppColors.error,
                        fontSize: 12.5,
                      ),
                    ),
                  ),
                _fieldLabel("WORKOUT"),
                const SizedBox(height: 6),
                if (_workoutsLoading)
                  const LinearProgressIndicator(
                    color: AppColors.accent,
                    backgroundColor: AppColors.bgCard,
                  )
                else if (_workoutsError != null)
                  Text(
                    _workoutsError!,
                    style: GoogleFonts.inter(color: AppColors.error, fontSize: 12.5),
                  )
                else
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
                      value: workouts.any((w) => w.id == _workoutId)
                          ? _workoutId
                          : null,
                      hint: Text(
                        "Select a workout",
                        style: GoogleFonts.inter(color: AppColors.textMuted),
                      ),
                      dropdownColor: AppColors.bgCard,
                      style: GoogleFonts.inter(color: AppColors.textPrimary),
                      icon: const Icon(
                        Icons.arrow_drop_down,
                        color: AppColors.accent,
                      ),
                      items: workouts
                          .map(
                            (w) => DropdownMenuItem(
                              value: w.id,
                              child: Text("${w.name} (${w.category})"),
                            ),
                          )
                          .toList(),
                      onChanged: (val) {
                        setState(() {
                          _workoutId = val;
                          if (_titleController.text.isEmpty && val != null) {
                            _titleController.text = workouts
                                .firstWhere((w) => w.id == val)
                                .name;
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
                        padding: const EdgeInsets.symmetric(
                          horizontal: 14,
                          vertical: 10,
                        ),
                        decoration: BoxDecoration(
                          color: selected ? AppColors.accent : AppColors.bgCard,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                            color: selected
                                ? AppColors.accent
                                : AppColors.border,
                          ),
                        ),
                        child: Text(
                          d.shortLabel,
                          style: GoogleFonts.oswald(
                            fontSize: 13,
                            fontWeight: FontWeight.bold,
                            color: selected
                                ? AppColors.bgPrimary
                                : AppColors.textPrimary,
                          ),
                        ),
                      ),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 14),
                Row(
                  children: [
                    Expanded(
                      child: _timeField(
                        "START TIME",
                        _startTime,
                        () => _pickTime(isStart: true),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _timeField(
                        "END TIME",
                        _endTime,
                        () => _pickTime(isStart: false),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 24),
                SizedBox(
                  width: double.infinity,
                  child: SlantedButton(
                    text: _isEditing ? "SAVE CHANGES" : "ADD SESSION",
                    icon: Icons.check,
                    isLoading: _saving,
                    isDisabled: _deleting,
                    onPressed: _submit,
                  ),
                ),
                if (_isEditing) ...[
                  const SizedBox(height: 12),
                  Center(
                    child: TextButton.icon(
                      onPressed: (_saving || _deleting) ? null : _delete,
                      icon: _deleting
                          ? const SizedBox(
                              width: 14,
                              height: 14,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                valueColor: AlwaysStoppedAnimation(
                                  AppColors.error,
                                ),
                              ),
                            )
                          : const Icon(
                              Icons.delete_outline,
                              size: 18,
                              color: AppColors.error,
                            ),
                      label: Text(
                        "DELETE SLOT",
                        style: GoogleFonts.oswald(
                          color: AppColors.error,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 1.0,
                        ),
                      ),
                    ),
                  ),
                ],
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
      style: GoogleFonts.oswald(
        fontSize: 13,
        fontWeight: FontWeight.bold,
        letterSpacing: 1.0,
        color: AppColors.textPrimary,
      ),
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
                const Icon(
                  Icons.access_time,
                  size: 16,
                  color: AppColors.accent,
                ),
                const SizedBox(width: 8),
                Text(
                  time.format(context),
                  style: GoogleFonts.inter(color: AppColors.textPrimary),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
