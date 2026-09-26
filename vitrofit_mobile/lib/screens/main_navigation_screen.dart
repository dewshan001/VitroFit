import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../state/app_state.dart';
import '../theme/app_theme.dart';
import 'home_screen.dart';
import 'profile_screen.dart';
import 'timetable_screen.dart';
import 'workouts_screen.dart';

class MainNavigationScreen extends StatefulWidget {
  const MainNavigationScreen({super.key});

  @override
  State<MainNavigationScreen> createState() => _MainNavigationScreenState();
}

class _MainNavigationScreenState extends State<MainNavigationScreen> {
  int _currentIndex = 0;

  late final List<Widget> _pages;

  @override
  void initState() {
    super.initState();
    _pages = [
      HomeScreen(onNavigateToTab: (index) {
        setState(() => _currentIndex = index);
      }),
      const WorkoutsScreen(),
      const TimetableScreen(),
      const ProfileScreen(),
    ];
  }

  void _showNotifications(BuildContext context) {
    final appState = context.read<AppState>();
    final upcoming = appState.timetableSlots.isNotEmpty ? appState.timetableSlots.first : null;
    final message = upcoming == null
        ? "No upcoming sessions on your timetable."
        : "Next up: ${upcoming.title} — ${upcoming.day.label} @ ${upcoming.startTime.label}";

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        backgroundColor: AppColors.bgCard,
        content: Text(message, style: GoogleFonts.inter(color: AppColors.textPrimary)),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final hasUpcoming = context.select<AppState, bool>((s) => s.timetableSlots.isNotEmpty);

    return Scaffold(
      backgroundColor: AppColors.bgPrimary,
      extendBodyBehindAppBar: false,
      appBar: PreferredSize(
        preferredSize: const Size.fromHeight(kToolbarHeight),
        child: ClipRect(
          child: BackdropFilter(
            filter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
            child: AppBar(
              backgroundColor: AppColors.bgPrimary.withOpacity(0.85),
              elevation: 0,
              scrolledUnderElevation: 0,
              titleSpacing: 20,
              title: Row(
                children: [
                  Container(
                    width: 10,
                    height: 24,
                    decoration: BoxDecoration(
                      color: AppColors.accent,
                      borderRadius: BorderRadius.circular(2),
                      boxShadow: const [BoxShadow(color: AppColors.shadowAccent, blurRadius: 10)],
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    "VITROFIT",
                    style: GoogleFonts.oswald(
                      fontSize: 24,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 2.5,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  const SizedBox(width: 4),
                  Container(
                    width: 6,
                    height: 6,
                    decoration: const BoxDecoration(color: AppColors.accent, shape: BoxShape.circle),
                  ),
                ],
              ),
              actions: [
                Stack(
                  children: [
                    IconButton(
                      icon: const Icon(Icons.notifications_none_rounded, color: AppColors.textPrimary),
                      onPressed: () => _showNotifications(context),
                    ),
                    if (hasUpcoming)
                      Positioned(
                        right: 10,
                        top: 10,
                        child: Container(
                          width: 8,
                          height: 8,
                          decoration: const BoxDecoration(color: AppColors.accent, shape: BoxShape.circle),
                        ),
                      ),
                  ],
                ),
                const SizedBox(width: 10),
              ],
            ),
          ),
        ),
      ),
      body: IndexedStack(
        index: _currentIndex,
        children: _pages,
      ),
      bottomNavigationBar: ClipRect(
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 16, sigmaY: 16),
          child: Container(
            decoration: BoxDecoration(
              color: AppColors.bgSecondary.withOpacity(0.9),
              border: const Border(top: BorderSide(color: AppColors.border, width: 1.0)),
            ),
            child: BottomNavigationBar(
              currentIndex: _currentIndex,
              onTap: (index) => setState(() => _currentIndex = index),
              backgroundColor: Colors.transparent,
              type: BottomNavigationBarType.fixed,
              selectedItemColor: AppColors.accent,
              unselectedItemColor: AppColors.textMuted,
              selectedLabelStyle: GoogleFonts.oswald(fontSize: 11, fontWeight: FontWeight.bold, letterSpacing: 1.0),
              unselectedLabelStyle: GoogleFonts.oswald(fontSize: 11, letterSpacing: 1.0),
              items: const [
                BottomNavigationBarItem(
                  icon: Icon(Icons.home_outlined),
                  activeIcon: Icon(Icons.home, color: AppColors.accent),
                  label: 'HOME',
                ),
                BottomNavigationBarItem(
                  icon: Icon(Icons.fitness_center_outlined),
                  activeIcon: Icon(Icons.fitness_center, color: AppColors.accent),
                  label: 'WORKOUTS',
                ),
                BottomNavigationBarItem(
                  icon: Icon(Icons.calendar_month_outlined),
                  activeIcon: Icon(Icons.calendar_month, color: AppColors.accent),
                  label: 'TIMETABLE',
                ),
                BottomNavigationBarItem(
                  icon: Icon(Icons.person_outline),
                  activeIcon: Icon(Icons.person, color: AppColors.accent),
                  label: 'PROFILE',
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
