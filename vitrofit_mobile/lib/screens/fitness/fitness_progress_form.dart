import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../models/fitness.dart';
import '../../theme/app_theme.dart';
import '../../widgets/agent_ui.dart';
import '../../widgets/slanted_button.dart';

String _fmt(DateTime d) =>
    '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

DateTime _parse(String s) {
  final p = s.split('-');
  return DateTime(int.parse(p[0]), int.parse(p[1]), int.parse(p[2]));
}

DateTime _dateOnly(DateTime d) => DateTime(d.year, d.month, d.day);

/// Records sessions for the current schedule. Beginner weeks (1-4) record one
/// session at a time; three-month blocks (5+) record every remaining day at
/// once, as on the web.
class FitnessProgressForm extends StatefulWidget {
  final FitnessWorkflow workflow;
  final List<FitnessProgressRecord> progress;
  final List<FitnessProgressRecord> previousWeekProgress;
  final bool busy;
  final String? error;

  /// Saves the sessions in order; returns true when all were saved.
  final Future<bool> Function(List<ProgressInput> inputs) onSave;

  const FitnessProgressForm({
    super.key,
    required this.workflow,
    required this.progress,
    required this.previousWeekProgress,
    required this.busy,
    required this.error,
    required this.onSave,
  });

  @override
  State<FitnessProgressForm> createState() => _FitnessProgressFormState();
}

class _Entry {
  final int day;
  DateTime date;
  int rpe = 5;
  bool incomplete = false;
  bool pain = false;
  bool noPainConfirmed = false;
  List<String> areas = [];
  _Entry(this.day, this.date);
}

class _FitnessProgressFormState extends State<FitnessProgressForm> {
  late FitnessPlan _plan;
  late List<FitnessPlanDay> _available;
  late DateTime _minimumDate;
  late String _priorCompleted;
  late final DateTime _planStart;

  // Single-session state.
  late int _day;
  late _Entry _single;

  // Batch state.
  late List<_Entry> _batch;

  String? _localError;

  bool get _isBlock => _plan.isBlock;

  @override
  void initState() {
    super.initState();
    _planStart = _parse(
      widget.workflow.createdAt.length >= 10
          ? widget.workflow.createdAt.substring(0, 10)
          : _fmt(DateTime.now()),
    );
    _rebuildFromProps();
  }

  @override
  void didUpdateWidget(FitnessProgressForm oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.progress != widget.progress ||
        oldWidget.workflow.id != widget.workflow.id) {
      _rebuildFromProps();
    }
  }

  void _rebuildFromProps() {
    _plan = widget.workflow.plan!;
    final completedDays = widget.progress
        .where((r) => r.countsAsRecorded)
        .map((r) => r.day)
        .toSet();
    _available = _plan.days.where((d) => !completedDays.contains(d.day)).toList();

    final dates = [
      ...widget.progress.map((r) => r.performedOn),
      ...widget.previousWeekProgress.map((r) => r.performedOn),
    ].where((d) => d.length == 10).toList()
      ..sort();
    _priorCompleted = dates.isEmpty ? '' : dates.last;
    _minimumDate = _priorCompleted.isNotEmpty
        ? _parse(_priorCompleted).add(const Duration(days: 1))
        : _planStart;
    _minimumDate = _dateOnly(_minimumDate);

    final today = _dateOnly(DateTime.now());
    final base = today.isBefore(_minimumDate) ? _minimumDate : today;

    _day = _available.isNotEmpty ? _available.first.day : _plan.days.first.day;
    _single = _Entry(_day, _nextDateForWeekday(_day, base));
    _batch = [
      for (var i = 0; i < _available.length; i++)
        _Entry(_available[i].day, base.add(Duration(days: i))),
    ];
  }

  DateTime _earliest() {
    final today = _dateOnly(DateTime.now());
    return today.isBefore(_minimumDate) ? _minimumDate : today;
  }

  DateTime _nextDateForWeekday(int weekday, DateTime start) {
    final offset = (weekday - start.weekday + 7) % 7;
    return start.add(Duration(days: offset));
  }

  int _dayNumber(int day) => _plan.days.indexWhere((d) => d.day == day) + 1;

  Future<DateTime?> _pickDate(DateTime initial, {int? weekday}) {
    final first = _minimumDate;
    var init = initial.isBefore(first) ? first : initial;
    if (weekday != null && init.weekday != weekday) {
      init = _nextDateForWeekday(weekday, init);
    }
    return showDatePicker(
      context: context,
      initialDate: init,
      firstDate: first,
      lastDate: first.add(const Duration(days: 365)),
      selectableDayPredicate: weekday == null
          ? null
          : (d) => d.weekday == weekday,
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
  }

  Future<void> _submitSingle() async {
    final e = _single;
    if (e.date.isBefore(_minimumDate) || e.date.weekday != _day) {
      setState(
        () => _localError =
            '${_priorCompleted.isNotEmpty ? 'Choose a date after the last completed session ($_priorCompleted).' : 'Choose a date on or after the schedule start (${_fmt(_planStart)}).'} The date must be a ${fitnessWeekdayLong[_day - 1]}.',
      );
      return;
    }
    if (e.pain && e.areas.isEmpty) {
      setState(
        () => _localError = 'Select the body area or muscle group affected by pain.',
      );
      return;
    }
    setState(() => _localError = null);
    await widget.onSave([_toInput(e)]);
  }

  Future<void> _submitBatch() async {
    for (final e in _batch) {
      if (e.pain && e.areas.isEmpty) {
        setState(
          () => _localError =
              'Day ${_dayNumber(e.day)}: select the body area or muscle group affected by pain.',
        );
        return;
      }
      if (e.date.isBefore(_minimumDate)) {
        setState(
          () => _localError =
              'Day ${_dayNumber(e.day)}: choose a date on or after ${_fmt(_minimumDate)}.',
        );
        return;
      }
    }
    setState(() => _localError = null);
    await widget.onSave(_batch.map(_toInput).toList());
  }

  ProgressInput _toInput(_Entry e) => ProgressInput(
    day: e.day,
    rpe: e.rpe,
    completed: !e.incomplete,
    pain: e.pain,
    affectedAreas: e.areas,
    performedOn: _fmt(e.date),
  );

  @override
  Widget build(BuildContext context) {
    final painReported = widget.progress.any((r) => r.pain);
    final error = _localError ?? widget.error;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (painReported) ...[
          const AgentBanner(
            isError: true,
            icon: Icons.healing,
            message:
                'Pain recorded. Stop any movement that causes pain. The next block avoids exercises targeting the affected area and continues suitable workouts for other areas. Significant, worsening, or persistent pain needs qualified professional guidance.',
          ),
          const SizedBox(height: 12),
        ],
        if (widget.progress.isNotEmpty) ...[
          const SectionTitle('Session progress'),
          const SizedBox(height: 6),
          for (var i = 0; i < _plan.days.length; i++)
            _sessionLine(i, _plan.days[i]),
          const SizedBox(height: 12),
        ],
        if (_available.isEmpty)
          const AgentBanner(
            message:
                'All planned days have been recorded. You can now generate your next schedule.',
            icon: Icons.check_circle_outline,
          )
        else
          AgentCard(
            accent: true,
            child: _isBlock ? _batchForm(error) : _singleForm(error),
          ),
      ],
    );
  }

  Widget _sessionLine(int index, FitnessPlanDay planDay) {
    final record = widget.progress.where((r) => r.day == planDay.day).firstOrNull;
    final text = record == null
        ? 'Not recorded yet'
        : record.completed
        ? 'Completed · ${record.performedOn}'
        : 'Saved · incomplete · ${record.performedOn}';
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        children: [
          Expanded(
            child: Text(
              'Day ${(index + 1).toString().padLeft(2, '0')}'
              '${_isBlock ? '' : ' · ${fitnessWeekdayLong[planDay.day - 1]}'}',
              style: GoogleFonts.inter(
                fontSize: 12.5,
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary,
              ),
            ),
          ),
          Text(
            text,
            style: GoogleFonts.inter(
              fontSize: 12,
              color: record?.completed == true
                  ? AppColors.success
                  : AppColors.textMuted,
            ),
          ),
        ],
      ),
    );
  }

  Widget _singleForm(String? error) {
    final e = _single;
    final canSave = e.pain || e.noPainConfirmed;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const AgentHeaderLite(
          eyebrow: 'Keep your plan adaptive',
          title: 'Record a session',
        ),
        const SizedBox(height: 12),
        const FieldLabel('Planned weekday'),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final d in _available)
              SelectChip(
                label:
                    'DAY ${_dayNumber(d.day).toString().padLeft(2, '0')} · ${fitnessWeekdayShort[d.day - 1].toUpperCase()}',
                selected: _day == d.day,
                onTap: widget.busy
                    ? null
                    : () => setState(() {
                        _day = d.day;
                        final fresh = _Entry(
                          d.day,
                          _nextDateForWeekday(d.day, _earliest()),
                        );
                        _single = fresh;
                        _localError = null;
                      }),
              ),
          ],
        ),
        const SizedBox(height: 12),
        _dateField(
          e.date,
          onTap: () async {
            final picked = await _pickDate(e.date, weekday: _day);
            if (picked != null) {
              setState(() {
                e.date = picked;
                _localError = null;
              });
            }
          },
        ),
        const SizedBox(height: 12),
        _rpeSlider(e),
        CheckRow(
          label: 'Did not complete this session',
          value: e.incomplete,
          onChanged: widget.busy ? null : (v) => setState(() => e.incomplete = v),
        ),
        _painBlock(e, single: true),
        if (!e.pain)
          CheckRow(
            label: 'No pain or discomfort during this session',
            value: e.noPainConfirmed,
            onChanged: widget.busy
                ? null
                : (v) => setState(() => e.noPainConfirmed = v),
          ),
        if (error != null) ...[
          const SizedBox(height: 10),
          AgentBanner(message: error, isError: true),
        ],
        const SizedBox(height: 12),
        SizedBox(
          width: double.infinity,
          child: SlantedButton(
            text: 'SAVE SESSION',
            icon: Icons.check,
            isLoading: widget.busy,
            isDisabled: !canSave,
            onPressed: _submitSingle,
          ),
        ),
      ],
    );
  }

  Widget _batchForm(String? error) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const AgentHeaderLite(
          eyebrow: '3-month block analysis',
          title: 'Record all workout days',
        ),
        const SizedBox(height: 6),
        Text(
          'Fill in performance and effort for all ${_batch.length} workout days. Recording them together triggers analysis and generates your next 3-month block.',
          style: GoogleFonts.inter(
            fontSize: 12.5,
            height: 1.4,
            color: AppColors.textSecondary,
          ),
        ),
        const SizedBox(height: 12),
        for (final e in _batch) ...[
          Container(
            margin: const EdgeInsets.only(bottom: 12),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppColors.bgSecondary,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: AppColors.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'DAY ${_dayNumber(e.day).toString().padLeft(2, '0')} · ${_plan.days.firstWhere((d) => d.day == e.day).focus}',
                  style: GoogleFonts.oswald(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                    color: AppColors.accent,
                  ),
                ),
                const SizedBox(height: 8),
                _dateField(
                  e.date,
                  onTap: () async {
                    final picked = await _pickDate(e.date);
                    if (picked != null) {
                      setState(() {
                        e.date = picked;
                        _localError = null;
                      });
                    }
                  },
                ),
                const SizedBox(height: 8),
                _rpeSlider(e),
                CheckRow(
                  label: 'Did not complete session',
                  value: e.incomplete,
                  onChanged: widget.busy
                      ? null
                      : (v) => setState(() => e.incomplete = v),
                ),
                _painBlock(e, single: false),
              ],
            ),
          ),
        ],
        if (error != null) ...[
          AgentBanner(message: error, isError: true),
          const SizedBox(height: 10),
        ],
        SizedBox(
          width: double.infinity,
          child: SlantedButton(
            text: 'SAVE ALL ${_batch.length} DAYS & ANALYZE',
            icon: Icons.analytics_outlined,
            isLoading: widget.busy,
            onPressed: _submitBatch,
          ),
        ),
        if (widget.busy)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              'Saving sessions & analysing block…',
              style: GoogleFonts.inter(fontSize: 12, color: AppColors.textMuted),
            ),
          ),
      ],
    );
  }

  Widget _dateField(DateTime date, {required VoidCallback onTap}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const FieldLabel('Date'),
        GestureDetector(
          onTap: widget.busy ? null : onTap,
          child: Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
            decoration: BoxDecoration(
              color: AppColors.bgCard,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: AppColors.border),
            ),
            child: Row(
              children: [
                const Icon(Icons.event, size: 16, color: AppColors.accent),
                const SizedBox(width: 8),
                Text(
                  '${fitnessWeekdayShort[date.weekday - 1]}, ${_fmt(date)}',
                  style: GoogleFonts.inter(color: AppColors.textPrimary),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _rpeSlider(_Entry e) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        FieldLabel('Effort (1 easy – 10 maximum): ${e.rpe}'),
        SliderTheme(
          data: SliderTheme.of(context).copyWith(
            activeTrackColor: AppColors.accent,
            thumbColor: AppColors.accent,
            inactiveTrackColor: AppColors.bgElevated,
            overlayColor: AppColors.accentGlow,
          ),
          child: Slider(
            min: 1,
            max: 10,
            divisions: 9,
            value: e.rpe.toDouble(),
            label: '${e.rpe}',
            onChanged: widget.busy ? null : (v) => setState(() => e.rpe = v.round()),
          ),
        ),
      ],
    );
  }

  Widget _painBlock(_Entry e, {required bool single}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        CheckRow(
          label: 'I experienced pain or discomfort',
          value: e.pain,
          onChanged: widget.busy
              ? null
              : (v) => setState(() {
                  e.pain = v;
                  if (v) e.noPainConfirmed = false;
                }),
        ),
        if (e.pain) ...[
          Padding(
            padding: const EdgeInsets.only(top: 6, bottom: 4),
            child: Text(
              'Where did you feel pain? Select all that apply.',
              style: GoogleFonts.inter(fontSize: 12, color: AppColors.textSecondary),
            ),
          ),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final area in fitnessBodyAreas)
                SelectChip(
                  label: area.toUpperCase(),
                  selected: e.areas.contains(area),
                  onTap: widget.busy
                      ? null
                      : () => setState(
                          () => e.areas.contains(area)
                              ? e.areas.remove(area)
                              : e.areas.add(area),
                        ),
                ),
            ],
          ),
        ],
      ],
    );
  }
}

/// Eyebrow + title used inside cards (smaller than [AgentHeader]).
class AgentHeaderLite extends StatelessWidget {
  final String eyebrow;
  final String title;
  const AgentHeaderLite({super.key, required this.eyebrow, required this.title});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          eyebrow.toUpperCase(),
          style: GoogleFonts.oswald(
            fontSize: 11,
            letterSpacing: 2,
            fontWeight: FontWeight.bold,
            color: AppColors.accent,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          title,
          style: GoogleFonts.oswald(
            fontSize: 20,
            fontWeight: FontWeight.bold,
            color: AppColors.textPrimary,
          ),
        ),
      ],
    );
  }
}
