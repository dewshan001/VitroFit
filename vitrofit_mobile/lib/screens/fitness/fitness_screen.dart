import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../api/agent_error.dart';
import '../../api/fitness_api.dart';
import '../../models/fitness.dart';
import '../../theme/app_theme.dart';
import '../../widgets/agent_ui.dart';
import '../../widgets/skeleton_box.dart';
import '../../widgets/slanted_button.dart';
import 'fitness_cycle_review_form.dart';
import 'fitness_plan_view.dart';
import 'fitness_profile_form.dart';
import 'fitness_progress_form.dart';

/// Fitness agent tab: profile → week-by-week plans → progress logging →
/// three-month blocks. Mirrors the web adaptive-fitness page.
class FitnessScreen extends StatefulWidget {
  const FitnessScreen({super.key});

  @override
  State<FitnessScreen> createState() => _FitnessScreenState();
}

class _FitnessScreenState extends State<FitnessScreen> {
  final _api = FitnessApi();

  bool _loaded = false;
  bool _busy = false;
  bool _editing = false;
  String? _pageError;
  String? _error;
  String? _notice;
  _Target _target = _Target.schedule;

  FitnessProfile? _profile;
  Map<String, FitnessExercise> _catalog = {};
  List<FitnessWorkflow> _schedules = []; // Ready, ordered by week
  FitnessWorkflow? _selected;
  FitnessHistory? _history;
  FitnessCycle? _nextCycle;
  Map<int, List<FitnessProgressRecord>> _progressByWeek = {};

  @override
  void initState() {
    super.initState();
    _load();
  }

  // --- loading -------------------------------------------------------------

  Future<void> _load() async {
    setState(() {
      _loaded = false;
      _pageError = null;
    });
    try {
      final exercisesFuture = _api.exercises();
      final profile = await _api.getProfile();
      final exercises = await exercisesFuture;
      if (!mounted) return;
      setState(() {
        _catalog = {for (final e in exercises) e.id: e};
        _profile = profile;
        _editing = profile == null;
      });
      await _refresh(profile);
    } on AgentException catch (e) {
      if (mounted) setState(() => _pageError = e.message);
    } finally {
      if (mounted) setState(() => _loaded = true);
    }
  }

  /// Loads one workflow with its history and cycle, and makes it the
  /// selected one (web `open`).
  Future<void> _open(String id) async {
    final results = await Future.wait([_api.workflow(id), _api.history(id)]);
    final workflow = results[0] as FitnessWorkflow;
    final audit = results[1] as FitnessHistory;
    final cycle = await _api.nextCycle(id);
    if (!mounted) return;
    setState(() {
      _selected = workflow;
      _history = audit;
      _nextCycle = cycle;
      if (workflow.plan != null) {
        _progressByWeek = {
          ..._progressByWeek,
          workflow.plan!.week: audit.progress,
        };
      }
    });
  }

  Future<void> _refresh(FitnessProfile? profile, {String? targetId}) async {
    final summaries = await _api.listWorkflows();
    final details = await Future.wait(summaries.map((s) => _api.workflow(s.id)));
    final ready = details.where((d) => d.isReady).toList()
      ..sort((a, b) => a.plan!.week.compareTo(b.plan!.week));
    final audits = await Future.wait(ready.map((d) => _api.history(d.id)));
    if (!mounted) return;

    setState(() {
      _progressByWeek = {
        for (var i = 0; i < ready.length; i++)
          ready[i].plan!.week: audits[i].progress,
      };
      _schedules = (profile?.reviewRequired ?? false) ? [] : ready;
    });

    final latest = details.isEmpty ? null : details.first;
    FitnessWorkflow? toOpen = latest;
    if (targetId != null) {
      toOpen = details.where((d) => d.id == targetId).firstOrNull ?? latest;
    }
    if (toOpen != null && !(profile?.reviewRequired ?? false)) {
      await _open(toOpen.id);
    } else if (mounted) {
      setState(() {
        _selected = latest?.status == 'ReviewRequired' ? latest : null;
        _history = null;
      });
    }
  }

  // --- actions -------------------------------------------------------------

  /// Runs [task] with busy/error handling; returns true on success.
  Future<bool> _action(
    Future<void> Function() task, {
    _Target target = _Target.schedule,
  }) async {
    setState(() {
      _busy = true;
      _error = null;
      _notice = null;
      _target = target;
    });
    try {
      await task();
      return true;
    } on AgentException catch (e) {
      if (mounted) setState(() => _error = e.message);
      return false;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _generate({String? previousId, FitnessProfile? profile}) async {
    final workflow = await _api.start(previousWorkflowId: previousId);
    await _open(workflow.id);
    await _refresh(profile ?? _profile);
    if (!mounted) return;
    setState(() {
      _notice = workflow.status == 'Ready'
          ? ((workflow.plan?.week ?? 0) > 4
                ? 'Workout block ${workflow.plan!.week - 4} is ready.'
                : 'Beginner schedule ${workflow.plan?.week ?? ''} is ready.')
          : (workflow.summary.isNotEmpty
                ? workflow.summary
                : 'The schedule could not be generated. See failure details below.');
    });
  }

  Future<void> _saveProfile(FitnessProfile data) async {
    await _action(() async {
      final saved = await _api.saveProfile(data);
      setState(() {
        _profile = saved;
        _editing = false;
      });
      if (saved.reviewRequired) {
        setState(() {
          _selected = null;
          _history = null;
          _schedules = [];
          _notice =
              'Profile saved. Your answer indicates a possible safety concern, so the self-scheduling agent is paused. Please get appropriate professional guidance.';
        });
        return;
      }
      final selected = _selected;
      if (selected == null ||
          (selected.status == 'ReviewRequired' &&
              selected.previousWorkflowId == null)) {
        await _generate(profile: saved);
      } else {
        setState(
          () => _notice =
              'Profile saved. Continue your current beginner schedule below.',
        );
      }
    }, target: _Target.profile);
  }

  Future<void> _deleteProfile() async {
    final ok = await confirmDialog(
      context,
      title: 'DELETE FITNESS PROFILE?',
      message:
          'Delete your fitness profile, schedules, and progress? Your VitroFit account will remain.',
      confirmLabel: 'DELETE',
      danger: true,
    );
    if (!ok || !mounted) return;
    await _action(() async {
      await _api.deleteProfile();
      setState(() {
        _profile = null;
        _selected = null;
        _history = null;
        _nextCycle = null;
        _schedules = [];
        _progressByWeek = {};
        _editing = true;
        _notice =
            'Fitness profile and its schedules were deleted. Your VitroFit account is unchanged.';
      });
    }, target: _Target.profile);
  }

  Future<bool> _saveProgress(List<ProgressInput> inputs) async {
    final selected = _selected;
    if (selected == null) return false;
    return _action(() async {
      for (final input in inputs) {
        await _api.saveProgress(selected.id, input);
      }
      await _open(selected.id);
      // Keep the shared schedule/log views in sync with the new records.
      setState(
        () => _notice = inputs.length > 1
            ? 'Sessions saved.'
            : 'Progress saved.',
      );
    }, target: _Target.progress);
  }

  Future<void> _submitCycleReview(CycleReviewInput review) async {
    final selected = _selected;
    if (selected == null) return;
    await _action(() async {
      final cycle = await _api.saveCycleReview(selected.id, review);
      final base = _profile;
      final updated = base?.copyWith(
        goal: review.goal,
        sessionMinutes: review.availableWorkoutMinutes,
        days: review.availableDays,
        equipment: review.equipment,
      );
      setState(() {
        _nextCycle = cycle;
        if (updated != null) _profile = updated;
      });
      await _generate(previousId: selected.id, profile: updated);
      if (mounted) {
        setState(
          () => _notice =
              'A new three-month training cycle has started with your next workout block.',
        );
      }
    });
  }

  Future<void> _regenerate(FitnessWorkflow selected) async {
    await _action(() async {
      final updated = await _api.regenerate(selected.id);
      await _refresh(_profile, targetId: selected.id);
      if (!mounted) return;
      setState(() {
        _notice = updated.status == 'Ready'
            ? ((updated.plan?.week ?? 0) > 4
                  ? 'Workout block ${updated.plan!.week - 4} regenerated.'
                  : 'Week ${updated.plan?.week} regenerated.')
            : (updated.summary.isNotEmpty
                  ? updated.summary
                  : 'Failed to regenerate schedule.');
      });
    });
  }

  // --- derived state (same rules as the web page) --------------------------

  bool _allDaysRecorded(FitnessWorkflow w) =>
      w.plan != null &&
      w.plan!.days.every(
        (day) => (_history?.progress ?? const []).any(
          (p) => p.day == day.day && p.countsAsRecorded,
        ),
      );

  // --- build ---------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      color: AppColors.accent,
      backgroundColor: AppColors.bgCard,
      onRefresh: _load,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(
          parent: BouncingScrollPhysics(),
        ),
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 120),
        children: [
          AgentHeader(
            eyebrow: _schedules.any((s) => s.plan!.week > 4)
                ? 'Adaptive training · Three-month cycle'
                : 'Adaptive training · Beginner series',
            title: 'TRAIN SMARTER.\nWEEK BY WEEK.',
            subtitle:
                'Build a routine around your goals. Your plan adapts as you log progress.',
          ),
          const SizedBox(height: 18),
          if (_pageError != null) ...[
            AgentBanner(message: _pageError!, isError: true),
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerLeft,
              child: AgentTextButton(
                label: 'Try again',
                icon: Icons.refresh,
                onPressed: _load,
              ),
            ),
          ] else if (!_loaded)
            ..._skeleton()
          else
            ..._content(),
        ],
      ),
    );
  }

  List<Widget> _skeleton() => const [
    SkeletonBox(height: 120, borderRadius: 16),
    SizedBox(height: 12),
    SkeletonBox(height: 220, borderRadius: 16),
  ];

  List<Widget> _content() {
    final profile = _profile;
    final selected = _selected;
    final widgets = <Widget>[];

    if (profile == null || _editing) {
      widgets.add(
        FitnessProfileForm(
          key: ValueKey(profile?.toJson().toString() ?? 'new'),
          initial: profile,
          busy: _busy,
          createSchedule:
              selected == null ||
              (selected.status == 'ReviewRequired' &&
                  selected.previousWorkflowId == null),
          onCancel: profile != null ? () => setState(() => _editing = false) : null,
          onSave: _saveProfile,
        ),
      );
      widgets.addAll(_feedback(_Target.profile));
      if (_busy && _target == _Target.profile) {
        widgets.add(_workingNote('Saving your profile and preparing your schedule…'));
      }
    } else {
      widgets.add(_profileSummary(profile));
      widgets.addAll(_feedback(_Target.profile));
    }

    widgets.add(const SizedBox(height: 16));

    if (selected == null && profile != null && profile.reviewRequired) {
      widgets.add(
        const AgentBanner(
          message:
              'Automated scheduling is paused because your profile indicates a health concern or need for review. If you selected this by mistake and it does not apply to you, update the health check before saving.',
        ),
      );
    } else if (selected == null && profile != null && _schedules.isEmpty) {
      widgets.add(
        const AgentBanner(
          message:
              'No schedule is available yet. Edit and save your profile to generate week 1.',
        ),
      );
    } else if (profile == null) {
      widgets.add(
        const AgentBanner(
          message: 'Create a fitness profile to generate your first schedule.',
        ),
      );
    }

    if (selected != null) widgets.addAll(_selectedPanel(selected, profile));
    return widgets;
  }

  Widget _workingNote(String text) => Padding(
    padding: const EdgeInsets.only(top: 10),
    child: AgentBanner(message: text, icon: Icons.hourglass_top),
  );

  List<Widget> _feedback(_Target target) {
    if (_target != target) return const [];
    return [
      if (_error != null)
        Padding(
          padding: const EdgeInsets.only(top: 10),
          child: AgentBanner(message: _error!, isError: true),
        ),
      if (_notice != null)
        Padding(
          padding: const EdgeInsets.only(top: 10),
          child: AgentBanner(message: _notice!, icon: Icons.check_circle_outline),
        ),
    ];
  }

  Widget _profileSummary(FitnessProfile p) {
    String row(String k, String v) => '$k: $v';
    return AgentCard(
      accent: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Expanded(child: SectionTitle('Your fitness profile')),
              Text(
                'PROFILE SAVED',
                style: GoogleFonts.oswald(
                  fontSize: 11,
                  letterSpacing: 1.2,
                  fontWeight: FontWeight.bold,
                  color: AppColors.accent,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 14,
            runSpacing: 6,
            children: [
              for (final line in [
                row('Target', fitnessGoals[p.goal] ?? p.goal),
                row('Age', '${p.age}'),
                row('Height', '${p.heightCm.round()} cm'),
                row('Weight', '${p.weightKg} kg'),
                row(
                  'Days',
                  p.days.map((d) => fitnessWeekdayShort[d - 1]).join(', '),
                ),
                row('Session', '${p.sessionMinutes} min'),
              ])
                Text(
                  line,
                  style: GoogleFonts.inter(
                    fontSize: 12.5,
                    color: AppColors.textSecondary,
                  ),
                ),
            ],
          ),
          const SizedBox(height: 6),
          Row(
            children: [
              AgentTextButton(
                label: 'Edit profile',
                icon: Icons.edit_outlined,
                onPressed: _busy ? null : () => setState(() => _editing = true),
              ),
              AgentTextButton(
                label: 'Delete',
                icon: Icons.delete_outline,
                danger: true,
                onPressed: _busy ? null : _deleteProfile,
              ),
            ],
          ),
        ],
      ),
    );
  }

  List<Widget> _selectedPanel(FitnessWorkflow selected, FitnessProfile? profile) {
    final plan = selected.plan;
    final ready = selected.status == 'Ready' && plan != null;
    final recorded = _allDaysRecorded(selected);
    final week = plan?.week ?? 0;

    final fourWeekCycleReady = ready && week == 4 && recorded;
    final currentBlockRecorded = ready && week > 4 && recorded;
    final today = DateTime.now();
    final todayStr =
        '${today.year.toString().padLeft(4, '0')}-${today.month.toString().padLeft(2, '0')}-${today.day.toString().padLeft(2, '0')}';
    final end = _nextCycle?.endDate;
    final cycleExpired = end != null && end.isNotEmpty && end.compareTo(todayStr) < 0;
    final blocks = week > 4 ? week - 4 : 0;
    final cycleCompleted =
        week > 4 &&
        ((blocks > 0 && blocks % 12 == 0 && currentBlockRecorded) || cycleExpired);
    final needsCycleReview =
        (fourWeekCycleReady && (_nextCycle == null || cycleExpired)) ||
        cycleCompleted;

    final titleText = week > 4
        ? 'Workout block ${week - 4}'
        : week > 0
        ? 'Beginner week $week of 4'
        : 'Schedule status';

    final failedEvents = (_history?.events ?? const <FitnessEvent>[])
        .where((e) => e.step == 'planner' || e.step == 'validator')
        .toList();
    final hasLaterSchedule = _schedules.any(
      (s) => s.previousWorkflowId == selected.id,
    );

    final w = <Widget>[
      AgentCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: AgentHeaderLite(
                    eyebrow: week > 4
                        ? 'Three-month schedule · Workout plan'
                        : 'Your training block',
                    title: titleText,
                  ),
                ),
                if (selected.status != 'Ready')
                  Text(
                    selected.status.toUpperCase(),
                    style: GoogleFonts.oswald(
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                      color: selected.status == 'Failed'
                          ? AppColors.error
                          : AppColors.info,
                    ),
                  ),
              ],
            ),
            if (ready) ...[
              const SizedBox(height: 12),
              FitnessPlanView(
                key: ValueKey('${selected.id}-${selected.version}'),
                schedules: _schedules.any((s) => s.id == selected.id)
                    ? _schedules
                    : [..._schedules, selected],
                catalog: _catalog,
                progressByWeek: _progressByWeek,
                initialWeek: week,
              ),
              if (selected.summary.isNotEmpty) ...[
                const SizedBox(height: 12),
                const SectionTitle('Progression guidance'),
                const SizedBox(height: 4),
                Text(
                  selected.summary,
                  style: GoogleFonts.inter(
                    fontSize: 12.5,
                    height: 1.4,
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ] else ...[
              const SizedBox(height: 8),
              Text(
                selected.summary,
                style: GoogleFonts.inter(
                  fontSize: 12.5,
                  height: 1.4,
                  color: AppColors.textSecondary,
                ),
              ),
            ],
            if (selected.safetyNote.isNotEmpty) ...[
              const SizedBox(height: 10),
              Text(
                'Safety reminder: ${selected.safetyNote}',
                style: GoogleFonts.inter(
                  fontSize: 11.5,
                  height: 1.4,
                  color: AppColors.textMuted,
                ),
              ),
            ],
          ],
        ),
      ),
    ];

    if (selected.status == 'ReviewRequired') {
      w.add(const SizedBox(height: 12));
      w.add(
        const AgentBanner(
          message:
              'The agent paused because your profile or progress indicates a concern. Please speak with an instructor or qualified health professional before continuing.',
        ),
      );
    }

    if (selected.status == 'Failed') {
      w.add(const SizedBox(height: 12));
      w.add(
        AgentBanner(
          isError: true,
          message: [
            'Failure details: ${selected.summary}',
            for (final e in failedEvents) '${e.step}: ${e.summary}',
            if (selected.summary.startsWith('Agent unavailable or interrupted'))
              'The agent service did not complete this request. Please try again in a moment.',
          ].join('\n'),
        ),
      );
      if (selected.previousWorkflowId == null) {
        w.add(const SizedBox(height: 10));
        w.add(
          _wideButton(
            'START A FRESH WEEK 1',
            Icons.restart_alt,
            () => _action(() => _generate()),
          ),
        );
      }
    }

    if (fourWeekCycleReady) {
      w.add(const SizedBox(height: 12));
      w.add(
        AgentCard(
          accent: true,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'You have completed the four beginner schedules! Review your current condition, pain or injuries, goals, available time, and equipment before continuing.',
                style: GoogleFonts.inter(
                  fontSize: 12.5,
                  height: 1.4,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 10),
              _wideButton(
                'GENERATE 3-MONTH SCHEDULE',
                Icons.auto_awesome,
                () => _action(() => _generate(previousId: selected.id)),
              ),
            ],
          ),
        ),
      );
    }

    if (week > 4) {
      w.add(const SizedBox(height: 12));
      if (cycleCompleted) {
        w.add(
          const AgentBanner(
            message:
                'Your three-month training cycle is complete. Review your condition, pain, goals, available workout time, and equipment to start your next 3-month training cycle.',
          ),
        );
        if (needsCycleReview) {
          w.add(const SizedBox(height: 10));
          w.add(
            FitnessCycleReviewForm(
              profile: profile,
              busy: _busy,
              onSubmit: _submitCycleReview,
            ),
          );
        }
      } else if (currentBlockRecorded) {
        w.add(
          _wideButton(
            'GENERATE NEXT 3-MONTH BLOCK',
            Icons.auto_awesome,
            () => _action(() => _generate(previousId: selected.id)),
          ),
        );
      } else {
        w.add(
          Text(
            'Record each workout day, including performance, effort, and any affected body area. Pain is saved and does not stop the whole program.',
            style: GoogleFonts.inter(fontSize: 12, color: AppColors.textMuted),
          ),
        );
      }
    }

    if (ready && !fourWeekCycleReady && !currentBlockRecorded) {
      w.add(const SizedBox(height: 14));
      w.add(
        FitnessProgressForm(
          key: ValueKey(selected.id),
          workflow: selected,
          progress: _history?.progress ?? const [],
          previousWeekProgress: _progressByWeek[week - 1] ?? const [],
          busy: _busy && _target == _Target.progress,
          error: _target == _Target.progress ? _error : null,
          onSave: _saveProgress,
        ),
      );
      if (week < 4) {
        w.add(const SizedBox(height: 10));
        w.add(
          _wideButton(
            'CREATE WEEK ${week + 1} OF 4 FROM MY PROGRESS',
            Icons.arrow_forward,
            _busy || !recorded
                ? null
                : () => _action(() => _generate(previousId: selected.id)),
          ),
        );
        if (!recorded) {
          w.add(
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Text(
                'Record each scheduled weekday before creating the next week. Pain reports remain in your history and guide a more conservative schedule.',
                style: GoogleFonts.inter(fontSize: 12, color: AppColors.textMuted),
              ),
            ),
          );
        }
      } else if (week == 4) {
        w.add(
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              'Record every scheduled day in week four to finish the four-week block and unlock your three-month schedule.',
              style: GoogleFonts.inter(fontSize: 12, color: AppColors.textMuted),
            ),
          ),
        );
      }
    }

    // Schedule-level feedback (progress feedback is shown inside the form).
    w.addAll(_feedback(_Target.schedule));
    if (_busy && _target == _Target.schedule) {
      w.add(
        _workingNote(
          'Working… generation can take up to two minutes. Do not submit again.',
        ),
      );
    }
    if (_notice != null && _target == _Target.progress && !_busy) {
      w.add(
        Padding(
          padding: const EdgeInsets.only(top: 10),
          child: AgentBanner(message: _notice!, icon: Icons.check_circle_outline),
        ),
      );
    }

    if (selected.status == 'Failed' || selected.status == 'Running') {
      w.add(const SizedBox(height: 10));
      w.add(
        _wideButton(
          'RETRY FAILED / INTERRUPTED REQUEST',
          Icons.refresh,
          _busy
              ? null
              : () => _action(() async {
                  await _api.retry(selected.id);
                  await _open(selected.id);
                }),
        ),
      );
    }

    if (ready && !hasLaterSchedule) {
      w.add(const SizedBox(height: 6));
      w.add(
        Center(
          child: AgentTextButton(
            label: 'Regenerate schedule',
            icon: Icons.refresh,
            onPressed: _busy ? null : () => _regenerate(selected),
          ),
        ),
      );
    }

    w.add(const SizedBox(height: 10));
    w.add(_activity());
    w.add(const SizedBox(height: 10));
    w.add(_recordedProgress());
    return w;
  }

  Widget _wideButton(String text, IconData icon, VoidCallback? onPressed) {
    return SizedBox(
      width: double.infinity,
      child: SlantedButton(
        text: text,
        icon: icon,
        isLoading: _busy && onPressed != null,
        isDisabled: onPressed == null,
        onPressed: onPressed ?? () {},
      ),
    );
  }

  Widget _activity() {
    final events = _history?.events ?? const <FitnessEvent>[];
    return AgentCard(
      padding: EdgeInsets.zero,
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          tilePadding: const EdgeInsets.symmetric(horizontal: 16),
          iconColor: AppColors.accent,
          collapsedIconColor: AppColors.textMuted,
          title: const SectionTitle('Schedule activity'),
          childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
          expandedCrossAxisAlignment: CrossAxisAlignment.start,
          children: events.isEmpty
              ? [
                  Text(
                    'No workflow activity has been recorded.',
                    style: GoogleFonts.inter(fontSize: 12, color: AppColors.textMuted),
                  ),
                ]
              : [
                  for (var i = 0; i < events.length; i++)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '${(i + 1).toString().padLeft(2, '0')} · ${events[i].step} · ${events[i].durationMs} ms',
                            style: GoogleFonts.oswald(
                              fontSize: 12,
                              color: AppColors.accent,
                            ),
                          ),
                          Text(
                            events[i].summary,
                            style: GoogleFonts.inter(
                              fontSize: 12,
                              color: AppColors.textSecondary,
                            ),
                          ),
                        ],
                      ),
                    ),
                ],
        ),
      ),
    );
  }

  Widget _recordedProgress() {
    final weeks = _progressByWeek.keys.where((k) => _progressByWeek[k]!.isNotEmpty).toList()
      ..sort();
    return AgentCard(
      padding: EdgeInsets.zero,
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          tilePadding: const EdgeInsets.symmetric(horizontal: 16),
          iconColor: AppColors.accent,
          collapsedIconColor: AppColors.textMuted,
          title: const SectionTitle('Recorded progress'),
          childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
          expandedCrossAxisAlignment: CrossAxisAlignment.start,
          children: weeks.isEmpty
              ? [
                  Text(
                    'No sessions have been recorded yet.',
                    style: GoogleFonts.inter(fontSize: 12, color: AppColors.textMuted),
                  ),
                ]
              : [
                  for (final week in weeks) ..._weekLog(week),
                ],
        ),
      ),
    );
  }

  List<Widget> _weekLog(int week) {
    final records = [..._progressByWeek[week]!]
      ..sort((a, b) => a.day.compareTo(b.day));
    final plan = _schedules.where((s) => s.plan!.week == week).firstOrNull?.plan;
    final done = records.where((r) => r.completed).length;
    return [
      Padding(
        padding: const EdgeInsets.only(top: 8, bottom: 4),
        child: Text(
          '${week <= 4 ? 'WEEK $week' : 'WORKOUT BLOCK ${week - 4}'} · $done of ${plan?.days.length ?? records.length} complete',
          style: GoogleFonts.oswald(
            fontSize: 13,
            fontWeight: FontWeight.bold,
            color: AppColors.textPrimary,
          ),
        ),
      ),
      for (final r in records)
        Padding(
          padding: const EdgeInsets.only(bottom: 3),
          child: Text(
            '${fitnessWeekdayShort[r.day - 1]} ${r.performedOn} · ${r.completed ? 'Completed' : 'Incomplete'} · effort ${r.rpe}/10'
            '${r.pain ? ' · Pain: ${r.affectedAreas.isEmpty ? 'area not specified' : r.affectedAreas.join(', ')}' : ''}',
            style: GoogleFonts.inter(
              fontSize: 12,
              color: r.pain ? AppColors.error : AppColors.textSecondary,
            ),
          ),
        ),
    ];
  }
}

enum _Target { profile, schedule, progress }
