import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../models/workout.dart';
import '../state/app_state.dart';
import '../theme/app_theme.dart';
import '../widgets/outline_text.dart';
import '../widgets/skeleton_box.dart';
import '../widgets/workout_card.dart';
import 'workout_detail_sheet.dart';

class WorkoutsScreen extends StatefulWidget {
  const WorkoutsScreen({super.key});

  @override
  State<WorkoutsScreen> createState() => _WorkoutsScreenState();
}

class _WorkoutsScreenState extends State<WorkoutsScreen> {
  String _searchQuery = '';
  String _selectedCategory = 'ALL';

  @override
  Widget build(BuildContext context) {
    final appState = context.watch<AppState>();
    final categories = ['ALL', ...{for (final w in appState.workouts) w.category}];
    if (!categories.contains(_selectedCategory)) _selectedCategory = 'ALL';

    final filtered = appState.workouts.where((w) {
      final matchesSearch = w.name.toLowerCase().contains(_searchQuery.toLowerCase()) ||
          w.category.toLowerCase().contains(_searchQuery.toLowerCase());
      final matchesCategory = _selectedCategory == 'ALL' || w.category == _selectedCategory;
      return matchesSearch && matchesCategory;
    }).toList();

    return RefreshIndicator(
      color: AppColors.accent,
      backgroundColor: AppColors.bgCard,
      onRefresh: () => context.read<AppState>().loadWorkouts(),
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(parent: BouncingScrollPhysics()),
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const OutlineText(text: "EXPLORE OUR", fontSize: 24),
            Text(
              "WORKOUT CATALOG",
              style: GoogleFonts.oswald(fontSize: 32, fontWeight: FontWeight.bold, letterSpacing: 1.5, color: AppColors.accent),
            ),
            const SizedBox(height: 6),
            Text(
              "Browse every workout in the studio's catalog and add the ones you want to your personal timetable.",
              style: GoogleFonts.inter(fontSize: 13, color: AppColors.textSecondary),
            ),
            const SizedBox(height: 20),
            TextField(
              onChanged: (val) => setState(() => _searchQuery = val),
              style: GoogleFonts.inter(color: AppColors.textPrimary),
              decoration: InputDecoration(
                hintText: "Search workout name or category...",
                hintStyle: GoogleFonts.inter(color: AppColors.textMuted),
                prefixIcon: const Icon(Icons.search, color: AppColors.accent),
                filled: true,
                fillColor: AppColors.bgCard,
                contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: AppColors.border)),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: const BorderSide(color: AppColors.accent, width: 1.5),
                ),
              ),
            ),
            const SizedBox(height: 16),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: categories.map((cat) {
                  final isSelected = _selectedCategory == cat;
                  return Padding(
                    padding: const EdgeInsets.only(right: 8.0),
                    child: FilterChip(
                      label: Text(cat, style: GoogleFonts.oswald(fontSize: 12, fontWeight: FontWeight.bold, color: isSelected ? AppColors.bgPrimary : AppColors.textPrimary)),
                      selected: isSelected,
                      onSelected: (selected) => setState(() => _selectedCategory = cat),
                      selectedColor: AppColors.accent,
                      backgroundColor: AppColors.bgCard,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(8),
                        side: BorderSide(color: isSelected ? AppColors.accent : AppColors.border),
                      ),
                    ),
                  );
                }).toList(),
              ),
            ),
            const SizedBox(height: 20),
            _buildBody(appState, filtered),
          ],
        ),
      ),
    );
  }

  Widget _buildBody(AppState appState, List<Workout> filtered) {
    if (appState.workoutsLoading && appState.workouts.isEmpty) {
      return Column(
        children: List.generate(4, (i) => const Padding(
              padding: EdgeInsets.only(bottom: 16),
              child: SkeletonBox(height: 150, borderRadius: 12),
            )),
      );
    }

    if (appState.workoutsError != null && appState.workouts.isEmpty) {
      return _messageBox(Icons.wifi_off, "Couldn't load workouts. Pull down to try again.\n${appState.workoutsError}");
    }

    if (filtered.isEmpty) {
      return _messageBox(Icons.fitness_center_sharp, "No workouts found matching your criteria.");
    }

    return Column(
      children: [
        Align(
          alignment: Alignment.centerLeft,
          child: Text(
            "SHOWING ${filtered.length} WORKOUTS",
            style: GoogleFonts.oswald(fontSize: 14, fontWeight: FontWeight.bold, letterSpacing: 1.0, color: AppColors.textMuted),
          ),
        ),
        const SizedBox(height: 12),
        ListView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: filtered.length,
          itemBuilder: (context, index) {
            final item = filtered[index];
            return Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: WorkoutCard(
                workout: item,
                onTap: () => WorkoutDetailSheet.show(context, item),
              ),
            ).animate(delay: (index * 60).ms).fadeIn(duration: 350.ms).slideY(begin: 0.12, end: 0, curve: Curves.easeOut);
          },
        ),
      ],
    );
  }

  Widget _messageBox(IconData icon, String message) {
    return Container(
      padding: const EdgeInsets.all(40),
      width: double.infinity,
      alignment: Alignment.center,
      child: Column(
        children: [
          Icon(icon, size: 48, color: AppColors.textMuted),
          const SizedBox(height: 12),
          Text(message, textAlign: TextAlign.center, style: GoogleFonts.inter(color: AppColors.textSecondary)),
        ],
      ),
    );
  }
}
