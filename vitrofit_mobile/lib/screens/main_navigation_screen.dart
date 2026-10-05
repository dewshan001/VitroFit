import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/app_theme.dart';
import '../widgets/chatbot_fab.dart';
import '../widgets/floating_nav_bar.dart';
import 'diet/diet_screen.dart';
import 'find_gym_screen.dart';
import 'fitness/fitness_screen.dart';
import 'home_screen.dart';
import 'profile_screen.dart';
import 'time/time_screen.dart';

class MainNavigationScreen extends StatefulWidget {
  const MainNavigationScreen({super.key});

  @override
  State<MainNavigationScreen> createState() => _MainNavigationScreenState();
}

class _MainNavigationScreenState extends State<MainNavigationScreen> {
  int _currentIndex = 0;
  bool _navBarVisible = true;

  /// Tabs are built the first time they are opened (not at app start), so the
  /// agent tabs only hit the backend when the user actually visits them.
  final Set<int> _visited = {NavTab.home};

  void _goToTab(int index) {
    setState(() {
      _currentIndex = index;
      _visited.add(index);
      _navBarVisible = true;
    });
  }

  Widget _tab(int index, Widget Function() build) =>
      _visited.contains(index) ? build() : const SizedBox.shrink();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgPrimary,
      // App Header
      appBar: AppBar(
        backgroundColor: AppColors.bgPrimary,
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
                boxShadow: const [
                  BoxShadow(
                    color: AppColors.shadowAccent,
                    blurRadius: 10,
                  )
                ],
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
              decoration: const BoxDecoration(
                color: AppColors.accent,
                shape: BoxShape.circle,
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.notifications_none_rounded, color: AppColors.textPrimary),
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  backgroundColor: AppColors.bgCard,
                  content: Text(
                    "No new notifications",
                    style: GoogleFonts.inter(color: AppColors.textPrimary),
                  ),
                ),
              );
            },
          ),
          const SizedBox(width: 10),
        ],
      ),

      // Body (IndexedStack preserves tab scroll states)
      // IndexedStack keeps each tab's state (and scroll position) alive.
      body: IndexedStack(
        index: _currentIndex,
        children: [
          HomeScreen(onNavigateToTab: _goToTab),
          _tab(NavTab.fitness, () => const FitnessScreen()),
          _tab(NavTab.gym, () => const FindGymScreen()),
          _tab(NavTab.diet, () => const DietScreen()),
          _tab(
            NavTab.time,
            () => TimeScreen(
              onNavigateToTab: _goToTab,
              active: _currentIndex == NavTab.time,
            ),
          ),
          _tab(NavTab.profile, () => const ProfileScreen()),
        ],
      ),
      floatingActionButton: const ChatbotFab(),
      floatingActionButtonLocation: FloatingActionButtonLocation.endFloat,
      bottomNavigationBar: IgnorePointer(
        ignoring: !_navBarVisible,
        child: AnimatedSlide(
          duration: const Duration(milliseconds: 280),
          curve: Curves.easeInOut,
          offset: _navBarVisible ? Offset.zero : const Offset(0, 1),
          child: AnimatedOpacity(
            duration: const Duration(milliseconds: 280),
            curve: Curves.easeInOut,
            opacity: _navBarVisible ? 1 : 0,
            child: FloatingNavBar(
              currentIndex: _currentIndex,
              onTap: _goToTab,
            ),
          ),
        ),
      ),
    );
  }
}
