import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../models/workout.dart';
import '../theme/app_theme.dart';
import '../widgets/badge_chip.dart';
import '../widgets/slanted_button.dart';
import '../widgets/workout_card.dart';
import 'timetable/timetable_slot_form.dart';

class WorkoutDetailSheet extends StatelessWidget {
  final Workout workout;

  const WorkoutDetailSheet({super.key, required this.workout});

  static void show(BuildContext context, Workout workout) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => WorkoutDetailSheet(workout: workout),
    );
  }

  void _addToTimetable(BuildContext sheetContext) {
    final rootContext = Navigator.of(sheetContext, rootNavigator: true).context;
    Navigator.of(sheetContext).pop();
    Future.microtask(() {
      if (rootContext.mounted) showTimetableSlotForm(rootContext, presetWorkout: workout);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: MediaQuery.of(context).size.height * 0.75,
      decoration: const BoxDecoration(
        color: AppColors.bgPrimary,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
        border: Border(top: BorderSide(color: AppColors.accent, width: 2)),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        children: [
          Container(
            margin: const EdgeInsets.only(top: 12, bottom: 8),
            width: 40,
            height: 4,
            decoration: BoxDecoration(color: AppColors.textMuted, borderRadius: BorderRadius.circular(2)),
          ),
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        width: 64,
                        height: 64,
                        decoration: BoxDecoration(
                          color: AppColors.bgCard,
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: AppColors.borderAccent),
                        ),
                        child: Icon(iconForCategory(workout.category), color: AppColors.accent, size: 32),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              workout.name,
                              style: GoogleFonts.oswald(fontSize: 24, fontWeight: FontWeight.bold, color: AppColors.textPrimary),
                            ),
                            const SizedBox(height: 4),
                            BadgeChip(label: workout.category),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),
                  Text(
                    "OVERVIEW",
                    style: GoogleFonts.oswald(fontSize: 16, fontWeight: FontWeight.bold, letterSpacing: 1.0, color: AppColors.textPrimary),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    (workout.description?.isNotEmpty ?? false)
                        ? workout.description!
                        : "No description has been added for this workout yet — check back soon.",
                    style: GoogleFonts.inter(fontSize: 14, height: 1.6, color: AppColors.textSecondary),
                  ),
                ],
              ),
            ),
          ),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: const BoxDecoration(
              color: AppColors.bgSecondary,
              border: Border(top: BorderSide(color: AppColors.border)),
            ),
            child: SizedBox(
              width: double.infinity,
              child: SlantedButton(
                text: "ADD TO MY TIMETABLE",
                icon: Icons.calendar_month,
                onPressed: () => _addToTimetable(context),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
