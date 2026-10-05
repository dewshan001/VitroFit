import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../../api/agent_error.dart';
import '../../api/time_agent_api.dart';
import '../../models/timetable_slot.dart';
import '../../state/app_state.dart';
import '../../theme/app_theme.dart';
import '../../widgets/agent_ui.dart';
import '../../widgets/skeleton_box.dart';
import '../../widgets/slanted_button.dart';
import 'timetable_slot_form.dart';

/// Time Management agent tab. It builds a weekly timetable from the user's
/// latest Ready fitness plan (so a fitness plan must exist first); once
/// generated, sessions can be adjusted by hand.
class TimeScreen extends StatefulWidget {
  /// Switches the main navigation to another tab (used to send the user to
  /// the Fitness tab when they have no plan yet).
  final ValueChanged<int> onNavigateToTab;

  /// True while this tab is the visible one; the plan is re-checked each time
  /// it becomes visible, since the Fitness tab may have created one meanwhile.
  final bool active;

  const TimeScreen({
    super.key,
    required this.onNavigateToTab,
    required this.active,
  });

  @override
  State<TimeScreen> createState() => _TimeScreenState();
}

class _TimeScreenState extends State<TimeScreen> {
  static const int _fitnessTabIndex = 1;

  final _api = TimeAgentApi();
  final _preferences = TextEditingController();

  ReadyFitnessPlan? _plan;
  bool _planLoading = true;
  bool _generating = false;
  String? _error;
  String? _notice;
  TimetableGeneration? _lastGeneration;

  @override
  void initState() {
    super.initState();
    _loadPlan();
    // Deferred: loadTimetable notifies listeners synchronously, which must
    // not happen while this widget tree is still being built.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) context.read<AppState>().loadTimetable();
    });
  }

  @override
  void didUpdateWidget(TimeScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.active && !oldWidget.active) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _refresh();
      });
    }
  }

  @override
  void dispose() {
    _preferences.dispose();
    super.dispose();
  }

  Future<void> _loadPlan() async {
    setState(() {
      _planLoading = true;
      _error = null;
    });
    try {
      final plan = await _api.latestReadyPlan();
      if (!mounted) return;
      setState(() => _plan = plan);
    } on AgentException catch (e) {
      if (!mounted) return;
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _planLoading = false);
    }
  }

  Future<void> _refresh() async {
    await Future.wait([_loadPlan(), context.read<AppState>().loadTimetable()]);
  }

  Future<void> _generate() async {
    final plan = _plan;
    if (plan == null || _generating) return;
    final appState = context.read<AppState>();

    if (appState.timetableSlots.isNotEmpty) {
      final ok = await confirmDialog(
        context,
        title: 'REPLACE TIMETABLE?',
        message:
            'Generating a new timetable replaces all of your current sessions, including any you edited by hand. Continue?',
        confirmLabel: 'REPLACE',
        danger: true,
      );
      if (!ok || !mounted) return;
    }

    setState(() {
      _generating = true;
      _error = null;
      _notice = null;
    });
    try {
      final result = await _api.generate(
        plan.workflowId,
        preferences: _preferences.text.trim(),
      );
      await appState.loadTimetable();
      if (!mounted) return;
      setState(() {
        _lastGeneration = result;
        _notice = result.status == 'ReviewRequired'
            ? 'The agent flagged this schedule for review. Please check it and speak with an instructor if anything looks wrong.'
            : 'Timetable generated with ${result.slotCount} sessions.';
      });
    } on AgentException catch (e) {
      if (!mounted) return;
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _generating = false);
    }
  }

  Future<void> _confirmDelete(TimetableSlot slot) async {
    final ok = await confirmRemoveTimetableSlot(context, slot.title);
    if (!ok || !mounted) return;
    try {
      await context.read<AppState>().deleteSlot(slot.id);
    } catch (e) {
      if (mounted) showAgentSnack(context, e.toString(), error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    final appState = context.watch<AppState>();
    final slots = appState.timetableSlots;

    return RefreshIndicator(
      color: AppColors.accent,
      backgroundColor: AppColors.bgCard,
      onRefresh: _refresh,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(
          parent: BouncingScrollPhysics(),
        ),
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 120),
        children: [
          const AgentHeader(
            eyebrow: 'Time management agent',
            title: 'SMART TIMETABLE',
            subtitle:
                'Turn your fitness plan into a weekly schedule that fits your day, then adjust it by hand.',
          ),
          const SizedBox(height: 18),
          _buildGeneratorCard(slots.isNotEmpty),
          if (_lastGeneration != null &&
              _lastGeneration!.longTermImpact.isNotEmpty) ...[
            const SizedBox(height: 14),
            AgentCard(
              accent: true,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SectionTitle('Long-term impact'),
                  const SizedBox(height: 6),
                  Text(
                    _lastGeneration!.longTermImpact,
                    style: GoogleFonts.inter(
                      fontSize: 13,
                      height: 1.45,
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
          ],
          const SizedBox(height: 22),
          _buildTimetable(appState, slots),
        ],
      ),
    );
  }

  Widget _buildGeneratorCard(bool hasTimetable) {
    if (_planLoading) {
      return const SkeletonBox(height: 150, borderRadius: 16);
    }

    final plan = _plan;
    return AgentCard(
      accent: plan != null,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SectionTitle('Smart scheduling'),
          const SizedBox(height: 10),
          if (plan == null) ...[
            const AgentBanner(
              message:
                  'No active fitness plan found. Create one in the Fitness tab first — the timetable is built from it.',
              icon: Icons.fitness_center,
            ),
            const SizedBox(height: 12),
            SlantedButton(
              text: 'GO TO FITNESS',
              icon: Icons.arrow_forward,
              paddingVertical: 10,
              paddingHorizontal: 18,
              onPressed: () => widget.onNavigateToTab(_fitnessTabIndex),
            ),
          ] else ...[
            Row(
              children: [
                const Icon(Icons.link, size: 16, color: AppColors.accent),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    'Based on: ${plan.title}',
                    style: GoogleFonts.inter(
                      fontSize: 12.5,
                      color: AppColors.textSecondary,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            const FieldLabel('Your preferences'),
            AgentTextArea(
              controller: _preferences,
              enabled: !_generating,
              hint:
                  'e.g. I prefer working out in the mornings, 1 hour lunch break at 12:00',
              maxLength: 300,
            ),
            const SizedBox(height: 4),
            SizedBox(
              width: double.infinity,
              child: SlantedButton(
                text: hasTimetable ? 'REGENERATE TIMETABLE' : 'GENERATE SMART TIMETABLE',
                icon: Icons.auto_awesome,
                isLoading: _generating,
                onPressed: _generate,
              ),
            ),
            if (_generating) ...[
              const SizedBox(height: 10),
              Text(
                'Working… this can take a minute. Please do not close the app.',
                style: GoogleFonts.inter(
                  fontSize: 12,
                  color: AppColors.textMuted,
                ),
              ),
            ],
          ],
          if (_error != null) ...[
            const SizedBox(height: 12),
            AgentBanner(message: _error!, isError: true),
          ],
          if (_notice != null) ...[
            const SizedBox(height: 12),
            AgentBanner(message: _notice!, icon: Icons.check_circle_outline),
          ],
        ],
      ),
    );
  }

  Widget _buildTimetable(AppState appState, List<TimetableSlot> slots) {
    if (appState.timetableLoading && slots.isEmpty) {
      return Column(
        children: List.generate(
          3,
          (i) => const Padding(
            padding: EdgeInsets.only(bottom: 10),
            child: SkeletonBox(height: 78, borderRadius: 12),
          ),
        ),
      );
    }

    if (slots.isEmpty) {
      return AgentCard(
        child: Row(
          children: [
            const Icon(Icons.event_note, color: AppColors.textMuted),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                _plan == null
                    ? 'Your timetable will appear here once you have a fitness plan and generate it.'
                    : 'No timetable yet. Generate one above to see your week here.',
                style: GoogleFonts.inter(
                  fontSize: 12.5,
                  color: AppColors.textSecondary,
                ),
              ),
            ),
          ],
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Expanded(child: SectionTitle('Your week')),
            AgentTextButton(
              label: 'Add session',
              icon: Icons.add,
              onPressed: () => showTimetableSlotForm(context),
            ),
          ],
        ),
        if (appState.timetableError != null)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: AgentBanner(message: appState.timetableError!, isError: true),
          ),
        const SizedBox(height: 6),
        for (final day in ApiDay.weekOrder) ..._buildDay(day, slots),
      ],
    );
  }

  List<Widget> _buildDay(ApiDay day, List<TimetableSlot> all) {
    final slots = all.where((s) => s.day == day).toList();
    return [
      Padding(
        padding: const EdgeInsets.only(top: 12, bottom: 6),
        child: Text(
          day.label.toUpperCase(),
          style: GoogleFonts.oswald(
            fontSize: 13,
            fontWeight: FontWeight.bold,
            letterSpacing: 1.4,
            color: slots.isEmpty ? AppColors.textMuted : AppColors.accent,
          ),
        ),
      ),
      if (slots.isEmpty)
        Text(
          'Rest day',
          style: GoogleFonts.inter(fontSize: 12, color: AppColors.textMuted),
        )
      else
        for (final slot in slots)
          _SlotCard(
            slot: slot,
            onEdit: () => showTimetableSlotForm(context, editingSlot: slot),
            onDelete: () => _confirmDelete(slot),
          ).animate().fadeIn(duration: 250.ms),
    ];
  }
}

class _SlotCard extends StatelessWidget {
  final TimetableSlot slot;
  final VoidCallback onEdit;
  final VoidCallback onDelete;

  const _SlotCard({
    required this.slot,
    required this.onEdit,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final lines = slot.descriptionLines;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onEdit,
        child: AgentCard(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.schedule, size: 16, color: AppColors.accent),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      '${slot.startTime.label} – ${slot.endTime.label}',
                      style: GoogleFonts.inter(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ),
                  if (slot.workoutCategory.isNotEmpty)
                    Text(
                      slot.workoutCategory,
                      style: GoogleFonts.inter(
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                        color: AppColors.accent,
                      ),
                    ),
                  IconButton(
                    visualDensity: VisualDensity.compact,
                    tooltip: 'Remove',
                    icon: const Icon(
                      Icons.delete_outline,
                      size: 18,
                      color: AppColors.textMuted,
                    ),
                    onPressed: onDelete,
                  ),
                ],
              ),
              Text(
                slot.title,
                style: GoogleFonts.oswald(
                  fontSize: 17,
                  fontWeight: FontWeight.bold,
                  color: AppColors.textPrimary,
                ),
              ),
              if (lines.isNotEmpty) ...[
                const SizedBox(height: 6),
                for (final line in lines)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 2),
                    child: Text(
                      '• $line',
                      style: GoogleFonts.inter(
                        fontSize: 12,
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
