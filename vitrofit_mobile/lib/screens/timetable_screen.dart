import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../models/timetable_slot.dart';
import '../state/app_state.dart';
import '../theme/app_theme.dart';
import '../widgets/badge_chip.dart';
import '../widgets/outline_text.dart';
import '../widgets/skeleton_box.dart';
import 'timetable/timetable_slot_form.dart';

class TimetableScreen extends StatefulWidget {
  const TimetableScreen({super.key});

  @override
  State<TimetableScreen> createState() => _TimetableScreenState();
}

class _TimetableScreenState extends State<TimetableScreen> {
  ApiDay _selectedDay = ApiDay.monday;

  Future<void> _confirmDelete(TimetableSlot slot) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColors.bgCard,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16), side: const BorderSide(color: AppColors.error)),
        title: Text("REMOVE SLOT?", style: GoogleFonts.oswald(fontWeight: FontWeight.bold, color: AppColors.error)),
        content: Text(
          "Remove \"${slot.title}\" from your timetable?",
          style: GoogleFonts.inter(color: AppColors.textSecondary),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text("CANCEL", style: GoogleFonts.oswald(color: AppColors.textMuted)),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text("REMOVE", style: GoogleFonts.oswald(color: AppColors.error, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );

    if (confirmed == true && mounted) {
      try {
        await context.read<AppState>().deleteSlot(slot.id);
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(backgroundColor: AppColors.error, content: Text(e.toString())),
          );
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final appState = context.watch<AppState>();
    final daySchedule = appState.timetableSlots.where((s) => s.day == _selectedDay).toList();

    return Scaffold(
      backgroundColor: Colors.transparent,
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => showTimetableSlotForm(context),
        backgroundColor: AppColors.accent,
        foregroundColor: AppColors.bgPrimary,
        icon: const Icon(Icons.add),
        label: Text("ADD SLOT", style: GoogleFonts.oswald(fontWeight: FontWeight.bold, letterSpacing: 1)),
      ),
      body: RefreshIndicator(
        color: AppColors.accent,
        backgroundColor: AppColors.bgCard,
        onRefresh: () => context.read<AppState>().loadTimetable(),
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(parent: BouncingScrollPhysics()),
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 100),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const OutlineText(text: "WEEKLY FITNESS", fontSize: 24),
              Text(
                "MY TIMETABLE",
                style: GoogleFonts.oswald(fontSize: 32, fontWeight: FontWeight.bold, letterSpacing: 1.5, color: AppColors.accent),
              ),
              const SizedBox(height: 6),
              Text(
                "Your personal weekly schedule. Add workouts from the catalog or build your own sessions.",
                style: GoogleFonts.inter(fontSize: 13, color: AppColors.textSecondary),
              ),
              const SizedBox(height: 20),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: ApiDay.weekOrder.map((day) {
                    final isSelected = _selectedDay == day;
                    final count = appState.timetableSlots.where((s) => s.day == day).length;
                    return GestureDetector(
                      onTap: () => setState(() => _selectedDay = day),
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 150),
                        margin: const EdgeInsets.only(right: 8),
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                        decoration: BoxDecoration(
                          color: isSelected ? AppColors.accent : AppColors.bgCard,
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: isSelected ? AppColors.accent : AppColors.border),
                          boxShadow: isSelected ? [BoxShadow(color: AppColors.accent.withOpacity(0.3), blurRadius: 10)] : [],
                        ),
                        child: Row(
                          children: [
                            Text(
                              day.shortLabel,
                              style: GoogleFonts.oswald(fontSize: 14, fontWeight: FontWeight.bold, color: isSelected ? AppColors.bgPrimary : AppColors.textPrimary),
                            ),
                            if (count > 0) ...[
                              const SizedBox(width: 6),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                                decoration: BoxDecoration(
                                  color: isSelected ? AppColors.bgPrimary : AppColors.accent,
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                child: Text(
                                  "$count",
                                  style: GoogleFonts.inter(fontSize: 10, fontWeight: FontWeight.bold, color: isSelected ? AppColors.accent : AppColors.bgPrimary),
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),
                    );
                  }).toList(),
                ),
              ),
              const SizedBox(height: 24),
              Text(
                "SESSIONS FOR ${_selectedDay.label}".toUpperCase(),
                style: GoogleFonts.oswald(fontSize: 16, fontWeight: FontWeight.bold, letterSpacing: 1.0, color: AppColors.textMuted),
              ),
              const SizedBox(height: 16),
              _buildBody(appState, daySchedule),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildBody(AppState appState, List<TimetableSlot> daySchedule) {
    if (appState.timetableLoading && appState.timetableSlots.isEmpty) {
      return Column(
        children: List.generate(3, (i) => const Padding(
              padding: EdgeInsets.only(bottom: 14),
              child: SkeletonBox(height: 90, borderRadius: 12),
            )),
      );
    }

    if (appState.timetableError != null && appState.timetableSlots.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(40),
        width: double.infinity,
        decoration: BoxDecoration(color: AppColors.bgCard, borderRadius: BorderRadius.circular(12)),
        child: Column(
          children: [
            const Icon(Icons.wifi_off, size: 40, color: AppColors.textMuted),
            const SizedBox(height: 12),
            Text("Couldn't load your timetable. Pull down to try again.", style: GoogleFonts.inter(color: AppColors.textSecondary), textAlign: TextAlign.center),
          ],
        ),
      );
    }

    if (daySchedule.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(40),
        width: double.infinity,
        decoration: BoxDecoration(color: AppColors.bgCard, borderRadius: BorderRadius.circular(12)),
        child: Column(
          children: [
            const Icon(Icons.event_busy, size: 40, color: AppColors.textMuted),
            const SizedBox(height: 12),
            Text(
              "No sessions scheduled for ${_selectedDay.label}. Tap ADD SLOT to plan one.",
              style: GoogleFonts.inter(color: AppColors.textSecondary),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: daySchedule.length,
      itemBuilder: (context, index) {
        final item = daySchedule[index];
        return Dismissible(
          key: ValueKey(item.id),
          direction: DismissDirection.endToStart,
          confirmDismiss: (_) async {
            await _confirmDelete(item);
            return false;
          },
          background: Container(
            alignment: Alignment.centerRight,
            padding: const EdgeInsets.symmetric(horizontal: 20),
            margin: const EdgeInsets.only(bottom: 14),
            decoration: BoxDecoration(color: AppColors.errorGlow, borderRadius: BorderRadius.circular(12)),
            child: const Icon(Icons.delete_outline, color: AppColors.error),
          ),
          child: GestureDetector(
            onTap: () => showTimetableSlotForm(context, editingSlot: item),
            child: Container(
              margin: const EdgeInsets.only(bottom: 14),
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppColors.bgCard,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppColors.border),
              ),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(color: AppColors.bgSecondary, borderRadius: BorderRadius.circular(8), border: Border.all(color: AppColors.border)),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(item.startTime.label, style: GoogleFonts.oswald(fontSize: 13, fontWeight: FontWeight.bold, color: AppColors.accent)),
                        Text("to ${item.endTime.label}", style: GoogleFonts.inter(fontSize: 10, color: AppColors.textMuted)),
                      ],
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(item.title, style: GoogleFonts.oswald(fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.textPrimary)),
                            ),
                            BadgeChip(label: item.workoutCategory, isAccent: false),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            const Icon(Icons.fitness_center, size: 14, color: AppColors.textMuted),
                            const SizedBox(width: 4),
                            Text(item.workoutName, style: GoogleFonts.inter(fontSize: 12, color: AppColors.textSecondary)),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const Icon(Icons.chevron_right, color: AppColors.textMuted),
                ],
              ),
            ),
          ),
        ).animate(delay: (index * 60).ms).fadeIn(duration: 300.ms).slideX(begin: 0.08, end: 0, curve: Curves.easeOut);
      },
    );
  }
}
