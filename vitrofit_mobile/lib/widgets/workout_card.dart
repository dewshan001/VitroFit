import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../models/workout.dart';
import '../theme/app_theme.dart';
import 'slanted_button.dart';

/// Icon chosen from the workout's category, purely for visual variety since
/// the backend's Workout catalog has no image field.
IconData iconForCategory(String category) {
  final c = category.toLowerCase();
  if (c.contains('yoga') || c.contains('mind')) return Icons.self_improvement;
  if (c.contains('strength') || c.contains('weight') || c.contains('lift')) return Icons.fitness_center;
  if (c.contains('cardio') || c.contains('run')) return Icons.directions_run;
  if (c.contains('cycle') || c.contains('spin')) return Icons.directions_bike;
  if (c.contains('pilates') || c.contains('core')) return Icons.accessibility_new;
  if (c.contains('box') || c.contains('combat') || c.contains('hiit')) return Icons.sports_kabaddi;
  return Icons.bolt;
}

class WorkoutCard extends StatefulWidget {
  final Workout workout;
  final VoidCallback onTap;

  const WorkoutCard({super.key, required this.workout, required this.onTap});

  @override
  State<WorkoutCard> createState() => _WorkoutCardState();
}

class _WorkoutCardState extends State<WorkoutCard> {
  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: widget.onTap,
      onTapDown: (_) => setState(() => _isHovered = true),
      onTapUp: (_) => setState(() => _isHovered = false),
      onTapCancel: () => setState(() => _isHovered = false),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        decoration: BoxDecoration(
          color: AppColors.bgCard,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: _isHovered ? AppColors.accent : AppColors.border,
            width: _isHovered ? 1.5 : 1.0,
          ),
          boxShadow: _isHovered
              ? [BoxShadow(color: AppColors.accent.withOpacity(0.2), blurRadius: 20, spreadRadius: 1)]
              : [BoxShadow(color: Colors.black.withOpacity(0.4), blurRadius: 10, offset: const Offset(0, 4))],
        ),
        clipBehavior: Clip.antiAlias,
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 48,
                  height: 48,
                  decoration: BoxDecoration(
                    color: AppColors.bgSecondary,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: AppColors.borderAccent),
                  ),
                  child: Icon(iconForCategory(widget.workout.category), color: AppColors.accent, size: 24),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        widget.workout.name.toUpperCase(),
                        style: GoogleFonts.oswald(fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.textPrimary),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      Text(
                        widget.workout.category,
                        style: GoogleFonts.inter(fontSize: 12, color: AppColors.accent, fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            if ((widget.workout.description ?? '').isNotEmpty) ...[
              const SizedBox(height: 12),
              Text(
                widget.workout.description!,
                style: GoogleFonts.inter(fontSize: 12.5, color: AppColors.textSecondary, height: 1.4),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],
            const SizedBox(height: 14),
            SizedBox(
              width: double.infinity,
              child: SlantedButton(
                text: "VIEW WORKOUT",
                onPressed: widget.onTap,
                isSecondary: !_isHovered,
                paddingVertical: 10,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
