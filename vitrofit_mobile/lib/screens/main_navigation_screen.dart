import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../state/app_state.dart';
import '../theme/app_theme.dart';
import '../widgets/chatbot_fab.dart';
import '../widgets/floating_nav_bar.dart';
import '../widgets/liquid_glass.dart';
import 'find_gym_screen.dart';
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
  bool _navBarVisible = true;

  late final List<Widget> _pages;

  @override
  void initState() {
    super.initState();
    _pages = [
      HomeScreen(
        onNavigateToTab: (index) {
          setState(() {
            _currentIndex = index;
            _navBarVisible = true;
          });
        },
      ),
      const WorkoutsScreen(),
      const TimetableScreen(),
      const FindGymScreen(),
      const ProfileScreen(),
    ];
  }

  bool _handleScrollNotification(UserScrollNotification notification) {
    if (notification.metrics.axis != Axis.vertical) return false;
    final direction = notification.direction;
    if (direction == ScrollDirection.reverse && _navBarVisible) {
      setState(() => _navBarVisible = false);
    } else if (direction == ScrollDirection.forward && !_navBarVisible) {
      setState(() => _navBarVisible = true);
    }
    return false;
  }

  void _showNotifications(BuildContext context) {
    final appState = context.read<AppState>();
    final upcoming = appState.timetableSlots.isNotEmpty
        ? appState.timetableSlots.first
        : null;
    final message = upcoming == null
        ? "No upcoming sessions on your timetable."
        : "Next up: ${upcoming.title} — ${upcoming.day.label} @ ${upcoming.startTime.label}";

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        backgroundColor: AppColors.bgCard,
        content: Text(
          message,
          style: GoogleFonts.inter(color: AppColors.textPrimary),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final hasUpcoming = context.select<AppState, bool>(
      (s) => s.timetableSlots.isNotEmpty,
    );

    return Scaffold(
      backgroundColor: AppColors.bgPrimary,
      extendBodyBehindAppBar: false,
      extendBody: true,
      appBar: PreferredSize(
        preferredSize: const Size.fromHeight(kToolbarHeight),
        child: LiquidGlassContainer(
          borderRadius: BorderRadius.zero,
          tint: AppColors.bgPrimary,
          tintOpacity: 0.78,
          blur: false,
          border: const Border(
            bottom: BorderSide(color: AppColors.border, width: 1),
          ),
          boxShadow: const [],
          child: AppBar(
            backgroundColor: Colors.transparent,
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
                      BoxShadow(color: AppColors.shadowAccent, blurRadius: 10),
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
              Stack(
                children: [
                  IconButton(
                    icon: const Icon(
                      Icons.notifications_none_rounded,
                      color: AppColors.textPrimary,
                    ),
                    onPressed: () => _showNotifications(context),
                  ),
                  if (hasUpcoming)
                    Positioned(
                      right: 10,
                      top: 10,
                      child: Container(
                        width: 8,
                        height: 8,
                        decoration: const BoxDecoration(
                          color: AppColors.accent,
                          shape: BoxShape.circle,
                        ),
                      ),
                    ),
                ],
              ),
              const SizedBox(width: 10),
            ],
          ),
        ),
      ),
      body: NotificationListener<UserScrollNotification>(
        onNotification: _handleScrollNotification,
        child: IndexedStack(index: _currentIndex, children: _pages),
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
              onTap: (index) => setState(() {
                _currentIndex = index;
                _navBarVisible = true;
              }),
            ),
          ),
        ),
      ),
    );
  }
}
