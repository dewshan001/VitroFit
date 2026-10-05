import 'dart:async';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../../api/agent_error.dart';
import '../../api/diet_api.dart';
import '../../models/diet.dart';
import '../../models/user_profile.dart';
import '../../state/app_state.dart';
import '../../theme/app_theme.dart';
import '../../widgets/agent_ui.dart';
import '../../widgets/skeleton_box.dart';
import '../../widgets/slanted_button.dart';
import 'diet_approvals_screen.dart';
import 'diet_form.dart';
import 'diet_plan_widgets.dart';

enum _Phase { loadingPlans, browse, empty, form, loading, result, pending, error, view }

/// Diet agent tab: preferences → live agent progress → plan (refine / confirm)
/// → saved plans. Mirrors the web DietPlan page.
class DietScreen extends StatefulWidget {
  const DietScreen({super.key});

  @override
  State<DietScreen> createState() => _DietScreenState();
}

class _DietScreenState extends State<DietScreen> {
  /// How long each agent card stays on screen before the next one appears,
  /// so a fast generation still reads at a human pace.
  static const _stepReveal = Duration(milliseconds: 3200);
  static const _pendingRefresh = Duration(seconds: 30);

  final _api = DietApi();
  final _scroll = ScrollController();

  _Phase _phase = _Phase.loadingPlans;
  DietPlan? _plan;
  DietPlan? _viewing;
  List<DietPlan> _saved = [];
  DietPrefs _lastPrefs = DietPrefs.defaults;
  int? _editingPlanId;

  // Live generation progress.
  List<DietStep> _liveSteps = [];
  StepContext _liveContext = const StepContext();

  // Error state.
  bool _loadFailed = false; // the saved-plans load failed (vs. a generation)
  String _errorMessage = '';
  List<DietStep> _errorSteps = [];

  // Refine / confirm state.
  bool _refining = false;
  String? _refineMessage;
  Set<String> _changedKeys = {};
  String _confirmStatus = 'idle'; // idle | saving | saved | error
  String? _confirmError;

  Timer? _pendingTimer;

  @override
  void initState() {
    super.initState();
    _initialLoad();
  }

  @override
  void dispose() {
    _pendingTimer?.cancel();
    _scroll.dispose();
    super.dispose();
  }

  // --- saved plans -----------------------------------------------------------

  Future<List<DietPlan>> _refreshSaved() async {
    try {
      final plans = await _api.savedPlans();
      if (mounted) {
        setState(() => _saved = plans);
        _syncPendingTimer();
      }
      return plans;
    } on AgentException {
      return _saved;
    }
  }

  Future<void> _initialLoad() async {
    setState(() => _phase = _Phase.loadingPlans);
    try {
      final plans = await _api.savedPlans();
      if (!mounted) return;
      setState(() {
        _saved = plans;
        _loadFailed = false;
        _phase = plans.isNotEmpty ? _Phase.browse : _Phase.empty;
      });
      _syncPendingTimer();
    } on AgentException catch (e) {
      if (!mounted) return;
      setState(() {
        _loadFailed = true;
        _errorMessage = e.message;
        _errorSteps = [];
        _phase = _Phase.error;
      });
    }
  }

  /// While any plan awaits specialist review, re-check the list so an approved
  /// plan shows its content and a declined one disappears.
  void _syncPendingTimer() {
    final hasPending = _saved.any((p) => p.isPending);
    if (hasPending && _pendingTimer == null) {
      _pendingTimer = Timer.periodic(_pendingRefresh, (_) async {
        final plans = await _refreshSaved();
        if (mounted && _phase == _Phase.browse && plans.isEmpty) {
          setState(() => _phase = _Phase.empty);
        }
      });
    } else if (!hasPending) {
      _pendingTimer?.cancel();
      _pendingTimer = null;
    }
  }

  void _goTo(_Phase phase) {
    setState(() => _phase = phase);
    if (_scroll.hasClients) {
      _scroll.animateTo(
        0,
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeOut,
      );
    }
  }

  // --- generation ------------------------------------------------------------

  Future<void> _generate(DietPrefs prefs) async {
    setState(() {
      _lastPrefs = prefs;
      _liveSteps = [];
      _liveContext = const StepContext();
      _confirmStatus = 'idle';
      _confirmError = null;
      _refineMessage = null;
      _changedKeys = {};
    });
    _goTo(_Phase.loading);
    try {
      final workflowId = await _api.generate(prefs);
      final plan = await _pollPaced(workflowId);
      if (!mounted) return;
      if (plan.requiresApproval) {
        // High-risk plan: saved as pending server-side; content stays hidden.
        setState(() {
          _plan = null;
          _editingPlanId = null;
        });
        await _refreshSaved();
        if (mounted) _goTo(_Phase.pending);
        return;
      }
      setState(() => _plan = plan);
      _goTo(_Phase.result);
    } on DietWorkflowFailed catch (e) {
      if (!mounted) return;
      setState(() {
        _loadFailed = false;
        _errorMessage = e.message;
        _errorSteps = e.steps;
      });
      _goTo(_Phase.error);
    } on AgentException catch (e) {
      if (!mounted) return;
      setState(() {
        _loadFailed = false;
        _errorMessage = e.message;
        _errorSteps = [];
      });
      _goTo(_Phase.error);
    }
  }

  /// Polls the workflow, revealing one completed step at a time. Resolves (or
  /// throws) only after every step up to the outcome has been shown.
  Future<DietPlan> _pollPaced(String workflowId) async {
    var latest = <DietStep>[];
    var latestRaw = <String, dynamic>{};
    var revealed = 0;
    var done = false;

    final revealLoop = () async {
      while (mounted) {
        if (revealed < latest.length) {
          await Future<void>.delayed(_stepReveal);
          if (!mounted) return;
          revealed++;
          setState(() {
            _liveSteps = latest.take(revealed).toList();
            _liveContext = StepContext.fromWorkflowJson(latestRaw);
          });
        } else if (done) {
          return;
        } else {
          await Future<void>.delayed(const Duration(milliseconds: 250));
        }
      }
    }();

    try {
      final plan = await _api.pollUntilDone(
        workflowId,
        onProgress: (s) {
          latest = s.steps;
          latestRaw = s.raw;
        },
      );
      latest = plan.steps;
      done = true;
      await revealLoop;
      return plan;
    } on DietWorkflowFailed catch (e) {
      latest = e.steps;
      done = true;
      await revealLoop;
      rethrow;
    } catch (_) {
      done = true;
      rethrow;
    }
  }

  Set<String> _diff(List<DietMeal> prev, List<DietMeal> next) {
    final prevByType = {for (final m in prev) m.type: m};
    final changed = <String>{};
    for (var i = 0; i < next.length; i++) {
      final prevMeal = prevByType[next[i].type];
      for (var j = 0; j < next[i].items.length; j++) {
        final prevItem = (prevMeal != null && j < prevMeal.items.length)
            ? prevMeal.items[j]
            : null;
        if (prevItem == null || prevItem.name != next[i].items[j].name) {
          changed.add('$i::$j');
        }
      }
    }
    return changed;
  }

  Future<void> _refine(String instruction) async {
    final plan = _plan;
    final id = plan?.workflowId;
    if (plan == null || id == null) return;
    setState(() {
      _refining = true;
      _refineMessage = null;
    });
    try {
      await _api.refine(id, instruction);
      final result = await _api.pollUntilDone(id);
      if (!mounted) return;
      setState(() {
        _plan = result;
        _changedKeys = result.note != null ? {} : _diff(plan.meals, result.meals);
        _refineMessage = result.note;
      });
    } on AgentException catch (e) {
      if (mounted) setState(() => _refineMessage = e.message);
    } finally {
      if (mounted) setState(() => _refining = false);
    }
  }

  Future<void> _confirm() async {
    final plan = _plan;
    if (plan == null) return;
    setState(() => _confirmStatus = 'saving');
    try {
      if (_editingPlanId != null) {
        await _api.updatePlan(_editingPlanId!, _lastPrefs, plan);
      } else {
        await _api.confirm(_lastPrefs, plan);
      }
      if (!mounted) return;
      setState(() {
        _confirmStatus = 'saved';
        _confirmError = null;
        _changedKeys = {};
      });
      await _refreshSaved();
    } on AgentException catch (e) {
      if (!mounted) return;
      setState(() {
        _confirmStatus = 'error';
        _confirmError = e.message;
      });
    }
  }

  void _createNew() {
    setState(() {
      _plan = null;
      _editingPlanId = null;
      _lastPrefs = DietPrefs.defaults;
      _confirmStatus = 'idle';
      _confirmError = null;
      _refineMessage = null;
      _changedKeys = {};
    });
    _goTo(_Phase.form);
  }

  void _editSaved(DietPlan p) {
    setState(() {
      _editingPlanId = p.id;
      _lastPrefs = p.inputs ?? DietPrefs.defaults;
      _plan = null;
      _confirmStatus = 'idle';
      _confirmError = null;
    });
    _goTo(_Phase.form);
  }

  void _viewSaved(DietPlan p) {
    if (p.isPending) return;
    setState(() => _viewing = p);
    _goTo(_Phase.view);
  }

  void _backToBrowse() {
    setState(() => _viewing = null);
    _goTo(_saved.isNotEmpty ? _Phase.browse : _Phase.empty);
  }

  Future<void> _delete(int id) async {
    final ok = await confirmDialog(
      context,
      title: 'DELETE PLAN?',
      message: 'Delete this diet plan? This cannot be undone.',
      confirmLabel: 'DELETE',
      danger: true,
    );
    if (!ok || !mounted) return;
    try {
      await _api.deletePlan(id);
      final plans = await _refreshSaved();
      if (!mounted) return;
      if (_viewing?.id == id) setState(() => _viewing = null);
      _goTo(plans.isNotEmpty ? _Phase.browse : _Phase.empty);
    } on AgentException catch (e) {
      if (mounted) showAgentSnack(context, e.message, error: true);
    }
  }

  void _cancelEdit() {
    if (_editingPlanId != null) {
      setState(() => _editingPlanId = null);
      _goTo(_saved.isNotEmpty ? _Phase.browse : _Phase.empty);
    } else {
      _goTo(_Phase.result);
    }
  }

  // --- build -----------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    final role = context.select<AppState, UserRole?>((s) => s.currentUser?.role);
    final isReviewer = role == UserRole.trainer || role == UserRole.admin;

    return ListView(
      controller: _scroll,
      physics: const BouncingScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 120),
      children: [
        const AgentHeader(
          eyebrow: 'VitroFit AI nutrition',
          title: 'PERSONALISED DIET\nPLANS FOR YOUR GOALS',
          subtitle:
              'Tell us about your body, goals and preferences to get a plan built meal by meal with realistic portions and macros.',
        ),
        if (isReviewer) ...[
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerLeft,
            child: AgentTextButton(
              label: 'Review pending plans',
              icon: Icons.fact_check_outlined,
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute<void>(builder: (_) => const DietApprovalsScreen()),
              ),
            ),
          ),
        ],
        const SizedBox(height: 14),
        ..._body(),
      ],
    );
  }

  List<Widget> _body() {
    switch (_phase) {
      case _Phase.loadingPlans:
        return const [SkeletonBox(height: 120, borderRadius: 16)];
      case _Phase.empty:
        return [_emptyState()];
      case _Phase.browse:
        return _browse();
      case _Phase.form:
        return [
          DietForm(
            initial: _lastPrefs,
            onSubmit: _generate,
            onCancel: (_plan != null || _editingPlanId != null) ? _cancelEdit : null,
          ),
        ];
      case _Phase.loading:
        return _loadingView();
      case _Phase.error:
        return [_errorView()];
      case _Phase.result:
        return _resultView();
      case _Phase.pending:
        return [_pendingView()];
      case _Phase.view:
        return _savedView();
    }
  }

  Widget _emptyState() => AgentCard(
    child: Column(
      children: [
        const Icon(Icons.restaurant_menu, size: 40, color: AppColors.accent),
        const SizedBox(height: 10),
        Text(
          'NO DIET PLAN YET',
          style: GoogleFonts.oswald(
            fontSize: 20,
            fontWeight: FontWeight.bold,
            color: AppColors.textPrimary,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          "Answer a few quick questions about your body, goals and dietary preferences and we'll generate a personalised plan for you.",
          textAlign: TextAlign.center,
          style: GoogleFonts.inter(
            fontSize: 12.5,
            height: 1.4,
            color: AppColors.textSecondary,
          ),
        ),
        const SizedBox(height: 14),
        SlantedButton(
          text: 'CREATE A NEW PLAN',
          icon: Icons.add,
          onPressed: _createNew,
        ),
      ],
    ),
  );

  List<Widget> _browse() {
    return [
      Row(
        children: [
          const Expanded(child: SectionTitle('Your diet plans')),
          AgentTextButton(label: 'New plan', icon: Icons.add, onPressed: _createNew),
        ],
      ),
      const SizedBox(height: 6),
      for (final p in _saved)
        Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: p.isPending ? _pendingCard(p) : _savedCard(p),
        ),
    ];
  }

  Widget _pendingCard(DietPlan p) => AgentCard(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          formatDietDate(p.createdAt),
          style: GoogleFonts.oswald(fontSize: 15, color: AppColors.textPrimary),
        ),
        const SizedBox(height: 4),
        Text(
          'AWAITING SPECIALIST REVIEW',
          style: GoogleFonts.oswald(
            fontSize: 12,
            fontWeight: FontWeight.bold,
            color: AppColors.info,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          "The plan's content will be available once a specialist approves it.",
          style: GoogleFonts.inter(fontSize: 12, color: AppColors.textMuted),
        ),
        AgentTextButton(
          label: 'Delete',
          icon: Icons.delete_outline,
          danger: true,
          onPressed: p.id == null ? null : () => _delete(p.id!),
        ),
      ],
    ),
  );

  Widget _savedCard(DietPlan p) => InkWell(
    borderRadius: BorderRadius.circular(16),
    onTap: () => _viewSaved(p),
    child: AgentCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            formatDietDate(p.createdAt),
            style: GoogleFonts.oswald(fontSize: 15, color: AppColors.textPrimary),
          ),
          Text(
            '${p.totalCalories.round()} kcal/day',
            style: GoogleFonts.inter(
              fontSize: 13,
              fontWeight: FontWeight.bold,
              color: AppColors.accent,
            ),
          ),
          Row(
            children: [
              AgentTextButton(
                label: 'Edit',
                icon: Icons.edit_outlined,
                onPressed: () => _editSaved(p),
              ),
              AgentTextButton(
                label: 'Delete',
                icon: Icons.delete_outline,
                danger: true,
                onPressed: p.id == null ? null : () => _delete(p.id!),
              ),
            ],
          ),
        ],
      ),
    ),
  );

  List<Widget> _loadingView() {
    return [
      AgentCard(
        accent: true,
        child: Row(
          children: [
            const SizedBox(
              width: 22,
              height: 22,
              child: CircularProgressIndicator(
                strokeWidth: 2.5,
                color: AppColors.accent,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                _liveSteps.isEmpty
                    ? 'Generating your diet plan… starting up the Nutrition Analyst.'
                    : 'Generating your diet plan…',
                style: GoogleFonts.inter(
                  fontSize: 13.5,
                  color: AppColors.textPrimary,
                ),
              ),
            ),
          ],
        ),
      ),
      const SizedBox(height: 12),
      for (final s in _liveSteps)
        AgentStepCard(step: s, context_: _liveContext, allSteps: _liveSteps),
      const SkeletonBox(height: 90, borderRadius: 12),
      const SizedBox(height: 10),
      const SkeletonBox(height: 90, borderRadius: 12),
    ];
  }

  Widget _errorView() {
    final attempts = _errorSteps.where((s) => s.agent == 'SafetyValidatorAgent').toList();
    return AgentCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            _loadFailed ? "COULDN'T LOAD YOUR PLANS" : "COULDN'T GENERATE YOUR PLAN",
            style: GoogleFonts.oswald(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: AppColors.error,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            _errorMessage.isEmpty
                ? 'Something went wrong while generating your diet plan. Please try again.'
                : _errorMessage,
            style: GoogleFonts.inter(fontSize: 13, height: 1.4, color: AppColors.textSecondary),
          ),
          if (attempts.isNotEmpty) ...[
            const SizedBox(height: 10),
            AgentBanner(
              message:
                  'Our system tried ${attempts.length == 1 ? 'once' : '${attempts.length} times'} to build a plan around your preferences:\n${attempts.map(_attemptLine).join('\n')}',
            ),
          ],
          const SizedBox(height: 14),
          if (_loadFailed)
            AgentTextButton(
              label: 'Try again',
              icon: Icons.refresh,
              onPressed: _initialLoad,
            )
          else
            Row(
              children: [
                AgentTextButton(
                  label: 'Edit preferences',
                  icon: Icons.tune,
                  onPressed: () => _goTo(_Phase.form),
                ),
                AgentTextButton(
                  label: 'Try again',
                  icon: Icons.refresh,
                  onPressed: () => _generate(_lastPrefs),
                ),
              ],
            ),
        ],
      ),
    );
  }

  String _attemptLine(DietStep s) {
    final label = s.attempt != null ? 'Try ${s.attempt}' : 'This try';
    if (s.verdict == 'pass') {
      return '$label: matched your calorie target and passed all checks.';
    }
    final safety = s.violations.any(
      (v) => v.code == 'RESTRICTION_VIOLATION' || v.code == 'BELOW_SAFE_FLOOR',
    );
    if (safety) {
      return '$label: one of the suggested meals conflicted with a restriction, allergy, or safe calorie minimum you set.';
    }
    final target = s.targetCalories;
    final attempt = s.attemptCalories;
    if (target != null && attempt != null) {
      return '$label: came out to about ${attempt.round()} calories — ${s.diffPct ?? '?'}% ${attempt < target ? 'short of' : 'over'} your ${target.round()}-calorie target.';
    }
    return "$label: didn't quite match your preferences.";
  }

  List<Widget> _resultView() {
    final plan = _plan;
    if (plan == null) return const [];
    final steps = plan.steps.where((s) => !s.refine).toList();
    final ctx = StepContext.fromPlan(plan);
    final saving = _confirmStatus == 'saving';
    final saved = _confirmStatus == 'saved';
    return [
      for (final s in steps) AgentStepCard(step: s, context_: ctx, allSteps: steps),
      DietPlanDetails(
        plan: plan,
        hasMedicalConditions: _lastPrefs.medicalConditions.isNotEmpty,
        changedKeys: _changedKeys,
      ),
      const SizedBox(height: 12),
      DietRefineBox(applying: _refining, message: _refineMessage, onRefine: _refine),
      const SizedBox(height: 14),
      Row(
        children: [
          AgentTextButton(
            label: 'Start over',
            icon: Icons.restart_alt,
            onPressed: saving ? null : () => _goTo(_Phase.form),
          ),
          Expanded(
            child: SlantedButton(
              text: saved ? 'PLAN SAVED ✓' : (saving ? 'SAVING…' : 'CONFIRM PLAN'),
              icon: Icons.check,
              isLoading: saving,
              isDisabled: saved,
              onPressed: _confirm,
            ),
          ),
        ],
      ),
      if (_confirmStatus == 'error') ...[
        const SizedBox(height: 10),
        AgentBanner(
          isError: true,
          message: _confirmError ?? "Couldn't save your plan. Please try again.",
        ),
      ],
      if (saved)
        Align(
          alignment: Alignment.centerLeft,
          child: AgentTextButton(
            label: 'Back to my plans',
            icon: Icons.arrow_back,
            onPressed: _backToBrowse,
          ),
        ),
    ];
  }

  Widget _pendingView() => AgentCard(
    child: Column(
      children: [
        const Icon(Icons.medical_services_outlined, size: 40, color: AppColors.info),
        const SizedBox(height: 10),
        Text(
          'SENT FOR SPECIALIST REVIEW',
          style: GoogleFonts.oswald(
            fontSize: 19,
            fontWeight: FontWeight.bold,
            color: AppColors.textPrimary,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          'Because of your health details, a nutrition specialist needs to check this plan before you can see it. It\'s saved in "Your diet plans" as awaiting review and will appear there once approved. If it is declined, it will be removed from your list.',
          textAlign: TextAlign.center,
          style: GoogleFonts.inter(fontSize: 12.5, height: 1.4, color: AppColors.textSecondary),
        ),
        const SizedBox(height: 14),
        SlantedButton(
          text: 'BACK TO MY PLANS',
          icon: Icons.arrow_back,
          onPressed: _backToBrowse,
        ),
      ],
    ),
  );

  List<Widget> _savedView() {
    final p = _viewing;
    if (p == null) return const [];
    return [
      DietPlanDetails(
        plan: p,
        hasMedicalConditions: (p.inputs?.medicalConditions ?? const []).isNotEmpty,
      ),
      const SizedBox(height: 12),
      Wrap(
        children: [
          AgentTextButton(label: 'Back', icon: Icons.arrow_back, onPressed: _backToBrowse),
          AgentTextButton(
            label: 'Edit',
            icon: Icons.edit_outlined,
            onPressed: () => _editSaved(p),
          ),
          AgentTextButton(
            label: 'Delete',
            icon: Icons.delete_outline,
            danger: true,
            onPressed: p.id == null ? null : () => _delete(p.id!),
          ),
        ],
      ),
    ];
  }
}
