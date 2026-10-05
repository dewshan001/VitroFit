import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../models/fitness.dart';
import '../../theme/app_theme.dart';
import '../../widgets/agent_ui.dart';

/// Shows the schedules (beginner weeks 1-4, then three-month blocks) with a
/// week picker, mirroring the web WorkoutPlanView in a phone-friendly layout.
class FitnessPlanView extends StatefulWidget {
  /// Ready schedules ordered by week.
  final List<FitnessWorkflow> schedules;
  final Map<String, FitnessExercise> catalog;
  final Map<int, List<FitnessProgressRecord>> progressByWeek;
  final int initialWeek;

  const FitnessPlanView({
    super.key,
    required this.schedules,
    required this.catalog,
    required this.progressByWeek,
    required this.initialWeek,
  });

  @override
  State<FitnessPlanView> createState() => _FitnessPlanViewState();
}

class _FitnessPlanViewState extends State<FitnessPlanView> {
  late int _week;

  @override
  void initState() {
    super.initState();
    _week = widget.initialWeek;
  }

  String _exerciseName(String id) => widget.catalog[id]?.name ?? id;

  @override
  Widget build(BuildContext context) {
    final plans = widget.schedules.where((s) => s.plan != null).toList();
    if (plans.isEmpty) return const SizedBox.shrink();
    final current = plans.firstWhere(
      (s) => s.plan!.week == _week,
      orElse: () => plans.last,
    );
    final plan = current.plan!;
    final records = widget.progressByWeek[plan.week] ?? const [];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (plans.length > 1) ...[
          SizedBox(
            height: 40,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: plans.length,
              separatorBuilder: (_, _) => const SizedBox(width: 8),
              itemBuilder: (context, i) {
                final p = plans[i].plan!;
                return SelectChip(
                  label: p.isBlock ? 'BLOCK ${p.blockNumber}' : 'WEEK ${p.week}',
                  selected: p.week == plan.week,
                  onTap: () => setState(() => _week = p.week),
                );
              },
            ),
          ),
          const SizedBox(height: 12),
        ],
        if (plan.isBlock)
          for (var i = 0; i < plan.days.length; i++)
            _DayCard(
              heading: 'DAY ${(i + 1).toString().padLeft(2, '0')}',
              weekday: null,
              day: plan.days[i],
              record: _recordFor(records, plan.days[i].day),
              nameOf: _exerciseName,
            )
        else
          for (var d = 1; d <= 7; d++) ...[
            () {
              final planDay = plan.days.where((x) => x.day == d).firstOrNull;
              if (planDay == null) {
                return _RestRow(weekday: fitnessWeekdayLong[d - 1]);
              }
              final index = plan.days.indexOf(planDay);
              return _DayCard(
                heading: 'DAY ${(index + 1).toString().padLeft(2, '0')}',
                weekday: fitnessWeekdayLong[d - 1],
                day: planDay,
                record: _recordFor(records, planDay.day),
                nameOf: _exerciseName,
              );
            }(),
          ],
      ],
    );
  }

  FitnessProgressRecord? _recordFor(
    List<FitnessProgressRecord> records,
    int day,
  ) {
    for (final r in records) {
      if (r.day == day) return r;
    }
    return null;
  }
}

class _RestRow extends StatelessWidget {
  final String weekday;
  const _RestRow({required this.weekday});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 4),
      child: Row(
        children: [
          SizedBox(
            width: 92,
            child: Text(
              weekday.toUpperCase(),
              style: GoogleFonts.oswald(
                fontSize: 12,
                letterSpacing: 1,
                color: AppColors.textMuted,
              ),
            ),
          ),
          Text(
            'Rest & recovery',
            style: GoogleFonts.inter(fontSize: 12, color: AppColors.textMuted),
          ),
        ],
      ),
    );
  }
}

class _DayCard extends StatelessWidget {
  final String heading;
  final String? weekday;
  final FitnessPlanDay day;
  final FitnessProgressRecord? record;
  final String Function(String id) nameOf;

  const _DayCard({
    required this.heading,
    required this.weekday,
    required this.day,
    required this.record,
    required this.nameOf,
  });

  @override
  Widget build(BuildContext context) {
    final r = record;
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: AgentCard(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  weekday == null ? heading : '$heading · ${weekday!.toUpperCase()}',
                  style: GoogleFonts.oswald(
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 1.2,
                    color: AppColors.accent,
                  ),
                ),
                const Spacer(),
                if (r != null)
                  Text(
                    r.completed
                        ? 'COMPLETED'
                        : r.pain
                        ? 'PAIN REPORTED'
                        : 'INCOMPLETE',
                    style: GoogleFonts.oswald(
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                      color: r.completed ? AppColors.success : AppColors.error,
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              day.focus,
              style: GoogleFonts.oswald(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: AppColors.textPrimary,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              [
                if (day.warmupMinutes > 0) 'Warm-up ${day.warmupMinutes} min',
                if (day.cooldownMinutes > 0) 'Cool-down ${day.cooldownMinutes} min',
                if (day.durationMinutes != null) '${day.durationMinutes} min total',
              ].join(' · '),
              style: GoogleFonts.inter(fontSize: 11.5, color: AppColors.textMuted),
            ),
            const SizedBox(height: 8),
            for (final e in day.exercises)
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          child: Text(
                            nameOf(e.exerciseId),
                            style: GoogleFonts.inter(
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                              color: AppColors.textPrimary,
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          '${e.sets} × ${e.repetitions} · rest ${e.restSeconds}s',
                          style: GoogleFonts.inter(
                            fontSize: 12,
                            color: AppColors.textSecondary,
                          ),
                        ),
                      ],
                    ),
                    if (e.adaptedFromExerciseId != null)
                      Text(
                        'Adapted from ${nameOf(e.adaptedFromExerciseId!)}'
                        '${e.adaptationReason != null ? ': ${e.adaptationReason}' : ''}',
                        style: GoogleFonts.inter(
                          fontSize: 11,
                          color: AppColors.info,
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
}
