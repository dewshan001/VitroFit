import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/app_theme.dart';
import 'liquid_glass.dart';

class NavBarItem {
  final IconData icon;
  final IconData activeIcon;
  final String label;

  const NavBarItem({
    required this.icon,
    required this.activeIcon,
    required this.label,
  });
}

const double _barHeight = 66;

/// A slim stadium-shaped glass dock. The active tab highlights in place with
/// a glowing accent chip around its (filled) icon - no detached elements.
class FloatingNavBar extends StatelessWidget {
  final int currentIndex;
  final ValueChanged<int> onTap;

  static const List<NavBarItem> items = [
    NavBarItem(
      icon: Icons.home_outlined,
      activeIcon: Icons.home,
      label: 'HOME',
    ),
    NavBarItem(
      icon: Icons.fitness_center_outlined,
      activeIcon: Icons.fitness_center,
      label: 'WORKOUTS',
    ),
    NavBarItem(
      icon: Icons.calendar_month_outlined,
      activeIcon: Icons.calendar_month,
      label: 'TIMETABLE',
    ),
    NavBarItem(
      icon: Icons.location_on_outlined,
      activeIcon: Icons.location_on,
      label: 'FIND GYM',
    ),
    NavBarItem(
      icon: Icons.person_outline,
      activeIcon: Icons.person,
      label: 'PROFILE',
    ),
  ];

  const FloatingNavBar({
    super.key,
    required this.currentIndex,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return SafeArea(
          top: false,
          minimum: const EdgeInsets.fromLTRB(28, 0, 28, 14),
          child: SizedBox(
            height: _barHeight,
            child: LiquidGlassContainer(
              borderRadius: BorderRadius.circular(_barHeight / 2),
              tint: AppColors.bgSecondary,
              tintOpacity: 0.72,
              blur: false,
              child: Row(
                children: List.generate(items.length, (i) {
                  final selected = i == currentIndex;
                  return Expanded(
                    child: _DockSlot(
                      item: items[i],
                      selected: selected,
                      onTap: () => onTap(i),
                    ),
                  );
                }),
              ),
            ),
          ),
        )
        .animate()
        .fadeIn(duration: 450.ms)
        .slideY(begin: 0.6, end: 0, curve: Curves.easeOutCubic);
  }
}

class _DockSlot extends StatefulWidget {
  final NavBarItem item;
  final bool selected;
  final VoidCallback onTap;

  const _DockSlot({
    required this.item,
    required this.selected,
    required this.onTap,
  });

  @override
  State<_DockSlot> createState() => _DockSlotState();
}

class _DockSlotState extends State<_DockSlot> {
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTapDown: (_) => setState(() => _pressed = true),
      onTapUp: (_) => setState(() => _pressed = false),
      onTapCancel: () => setState(() => _pressed = false),
      onTap: widget.onTap,
      child: AnimatedScale(
        scale: _pressed ? 0.85 : 1.0,
        duration: const Duration(milliseconds: 120),
        curve: Curves.easeOut,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            AnimatedContainer(
              duration: const Duration(milliseconds: 180),
              curve: Curves.easeOut,
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: widget.selected
                    ? AppColors.accent.withValues(alpha: 0.15)
                    : Colors.transparent,
                borderRadius: BorderRadius.circular(14),
                boxShadow: widget.selected
                    ? const [
                        BoxShadow(
                          color: AppColors.shadowAccent,
                          blurRadius: 10,
                        ),
                      ]
                    : null,
              ),
              child: Icon(
                widget.selected ? widget.item.activeIcon : widget.item.icon,
                color: widget.selected
                    ? AppColors.accent
                    : AppColors.textMuted,
                size: 22,
              ),
            ),
            const SizedBox(height: 4),
            AnimatedDefaultTextStyle(
              duration: const Duration(milliseconds: 220),
              curve: Curves.easeOut,
              style: GoogleFonts.oswald(
                fontSize: 10,
                letterSpacing: 0.6,
                fontWeight: widget.selected ? FontWeight.bold : FontWeight.w500,
                color: widget.selected ? AppColors.accent : AppColors.textMuted,
              ),
              child: Text(widget.item.label),
            ),
          ],
        ),
      ),
    );
  }
}
