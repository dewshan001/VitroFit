import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../api/agent_error.dart';
import '../../api/diet_api.dart';
import '../../models/diet.dart';
import '../../theme/app_theme.dart';
import '../../widgets/agent_ui.dart';
import '../../widgets/skeleton_box.dart';
import '../../widgets/slanted_button.dart';
import 'diet_plan_widgets.dart';

/// Trainer / Admin queue of high-risk diet plans waiting for a decision
/// (mirrors the web "Diet Approvals" admin tab).
class DietApprovalsScreen extends StatefulWidget {
  const DietApprovalsScreen({super.key});

  @override
  State<DietApprovalsScreen> createState() => _DietApprovalsScreenState();
}

class _DietApprovalsScreenState extends State<DietApprovalsScreen> {
  final _api = DietApi();
  List<DietApprovalItem> _rows = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final rows = await _api.pendingApprovals();
      if (mounted) setState(() => _rows = rows);
    } on AgentException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _review(DietApprovalItem row) async {
    final changed = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => _ReviewSheet(row: row, api: _api),
    );
    if (changed == true) _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgPrimary,
      appBar: AppBar(
        backgroundColor: AppColors.bgPrimary,
        title: Text(
          'DIET APPROVALS',
          style: GoogleFonts.oswald(
            fontWeight: FontWeight.bold,
            letterSpacing: 1.5,
          ),
        ),
      ),
      body: RefreshIndicator(
        color: AppColors.accent,
        backgroundColor: AppColors.bgCard,
        onRefresh: _load,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(20),
          children: [
            if (_loading)
              const SkeletonBox(height: 100, borderRadius: 12)
            else if (_error != null)
              AgentBanner(message: _error!, isError: true)
            else if (_rows.isEmpty)
              const AgentBanner(
                message: 'No diet plans are waiting for approval.',
                icon: Icons.check_circle_outline,
              )
            else
              for (final r in _rows)
                Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: InkWell(
                    borderRadius: BorderRadius.circular(16),
                    onTap: () => _review(r),
                    child: AgentCard(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Expanded(
                                child: Text(
                                  'Customer #${r.userId}',
                                  style: GoogleFonts.oswald(
                                    fontSize: 16,
                                    fontWeight: FontWeight.bold,
                                    color: AppColors.textPrimary,
                                  ),
                                ),
                              ),
                              Text(
                                r.riskLevel.toUpperCase(),
                                style: GoogleFonts.oswald(
                                  fontSize: 12,
                                  fontWeight: FontWeight.bold,
                                  color: AppColors.error,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 4),
                          Text(
                            r.riskFlags.isEmpty
                                ? 'No flags listed'
                                : r.riskFlags.map(riskFlagLabel).join(', '),
                            style: GoogleFonts.inter(
                              fontSize: 12.5,
                              color: AppColors.textSecondary,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '${r.totalCalories} kcal/day · ${formatDietDate(r.createdAt)}',
                            style: GoogleFonts.inter(
                              fontSize: 12,
                              color: AppColors.textMuted,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
          ],
        ),
      ),
    );
  }
}

class _ReviewSheet extends StatefulWidget {
  final DietApprovalItem row;
  final DietApi api;
  const _ReviewSheet({required this.row, required this.api});

  @override
  State<_ReviewSheet> createState() => _ReviewSheetState();
}

class _ReviewSheetState extends State<_ReviewSheet> {
  final _note = TextEditingController();
  DietPlan? _plan;
  Map<String, dynamic>? _raw;
  bool _loading = true;
  bool _declining = false;
  bool _deciding = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _note.addListener(() => setState(() {}));
    _load();
  }

  @override
  void dispose() {
    _note.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final status = await widget.api.workflow(widget.row.workflowId);
      if (!mounted) return;
      setState(() {
        _raw = status.raw;
        _plan = DietPlan.fromWorkflow(status.raw);
      });
    } on AgentException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _decide(bool approve) async {
    setState(() {
      _deciding = true;
      _error = null;
    });
    try {
      await widget.api.decide(
        widget.row.workflowId,
        approve: approve,
        note: _note.text.trim(),
      );
      if (mounted) Navigator.of(context).pop(true);
    } on AgentException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _deciding = false);
    }
  }

  List<Widget> _customerData(DietPrefs p) {
    String list(List<String> l) => l.isEmpty ? 'None' : l.join(', ');
    final rows = <(String, String)>[
      ('Age / gender', '${p.age} · ${p.gender}'),
      ('Height / weight', '${p.heightCm} cm · ${p.weightKg} kg'),
      ('Activity level', p.activityLevel),
      ('Goal', p.goal),
      ('Medical conditions', list(p.medicalConditions)),
      ('Dietary restrictions', list(p.restrictions)),
      ('Dislikes', p.dislikes.isEmpty ? 'None' : p.dislikes),
      (
        'Budget',
        '${p.budgetTier}${p.budgetCustomAmount != null ? ' (${p.budgetCustomAmount})' : ''}',
      ),
      ('Meals / cooking time', '${p.mealFrequency} · ${p.cookingTime}'),
    ];
    return [
      for (final r in rows)
        Padding(
          padding: const EdgeInsets.only(bottom: 4),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SizedBox(
                width: 130,
                child: Text(
                  r.$1,
                  style: GoogleFonts.inter(
                    fontSize: 12,
                    color: AppColors.textMuted,
                  ),
                ),
              ),
              Expanded(
                child: Text(
                  r.$2,
                  style: GoogleFonts.inter(
                    fontSize: 12.5,
                    color: AppColors.textPrimary,
                  ),
                ),
              ),
            ],
          ),
        ),
    ];
  }

  @override
  Widget build(BuildContext context) {
    final plan = _plan;
    final flags = widget.row.riskFlags;
    return Padding(
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
      ),
      child: Container(
        constraints: BoxConstraints(
          maxHeight: MediaQuery.of(context).size.height * 0.9,
        ),
        decoration: const BoxDecoration(
          color: AppColors.bgPrimary,
          borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          border: Border(top: BorderSide(color: AppColors.accent, width: 2)),
        ),
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'DIET PLAN REVIEW · CUSTOMER #${widget.row.userId}',
                style: GoogleFonts.oswald(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: AppColors.accent,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                'Generated ${formatDietDate(widget.row.createdAt)}. Approving makes the plan visible to the customer; declining removes it from their list.',
                style: GoogleFonts.inter(
                  fontSize: 12,
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: 14),
              const SectionTitle('Why it needs review'),
              const SizedBox(height: 4),
              Text(
                'Risk: ${widget.row.riskLevel}${flags.isNotEmpty ? ' — ${flags.map(riskFlagLabel).join(', ')}' : ''}',
                style: GoogleFonts.inter(
                  fontSize: 13,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 14),
              if (_loading)
                const SkeletonBox(height: 120, borderRadius: 12)
              else ...[
                if (plan?.inputs != null) ...[
                  const SectionTitle('Customer data'),
                  const SizedBox(height: 6),
                  ..._customerData(plan!.inputs!),
                  const SizedBox(height: 14),
                ],
                if (plan != null && plan.meals.isNotEmpty) ...[
                  const SectionTitle('Generated plan'),
                  const SizedBox(height: 8),
                  DietPlanDetails(plan: plan, hasMedicalConditions: false),
                ] else if (_raw != null)
                  const AgentBanner(
                    message: 'This plan has no meal content to show.',
                  ),
              ],
              if (_declining) ...[
                const SizedBox(height: 14),
                const FieldLabel('Reason for declining (required)'),
                AgentTextArea(
                  controller: _note,
                  hint: 'Explain why this plan is declined',
                  maxLength: 1000,
                  minLines: 2,
                  enabled: !_deciding,
                ),
              ],
              if (_error != null) ...[
                const SizedBox(height: 10),
                AgentBanner(message: _error!, isError: true),
              ],
              const SizedBox(height: 14),
              if (plan != null && !_declining)
                Row(
                  children: [
                    Expanded(
                      child: AgentTextButton(
                        label: 'Decline',
                        icon: Icons.close,
                        danger: true,
                        onPressed: _deciding
                            ? null
                            : () => setState(() => _declining = true),
                      ),
                    ),
                    Expanded(
                      child: SlantedButton(
                        text: 'APPROVE',
                        icon: Icons.check,
                        isLoading: _deciding,
                        paddingHorizontal: 18,
                        onPressed: () => _decide(true),
                      ),
                    ),
                  ],
                ),
              if (plan != null && _declining)
                Row(
                  children: [
                    Expanded(
                      child: AgentTextButton(
                        label: 'Back',
                        icon: Icons.arrow_back,
                        onPressed: _deciding
                            ? null
                            : () => setState(() => _declining = false),
                      ),
                    ),
                    Expanded(
                      child: SlantedButton(
                        text: 'CONFIRM DECLINE',
                        icon: Icons.close,
                        isLoading: _deciding,
                        isDisabled: _note.text.trim().isEmpty,
                        paddingHorizontal: 14,
                        onPressed: () => _decide(false),
                      ),
                    ),
                  ],
                ),
              Center(
                child: AgentTextButton(
                  label: 'Close',
                  icon: Icons.keyboard_arrow_down,
                  onPressed: _deciding
                      ? null
                      : () => Navigator.of(context).pop(false),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
