import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/app_theme.dart';

class NavBarItem {
  final IconData icon;
  final IconData activeIcon;
  final String label;

  const NavBarItem({required this.icon, required this.activeIcon, required this.label});
}

const double _barHeight = 66;
const double _bubbleSize = 52;
const double _overflow = 20; // how far the bubble pokes above the bar

/// A detached "bubble dock": a slim stadium bar where the active tab's icon
/// lifts into a glowing floating bubble that glides between tabs.
class FloatingNavBar extends StatelessWidget {
  final int currentIndex;
  final ValueChanged<int> onTap;

  static const List<NavBarItem> items = [
    NavBarItem(icon: Icons.home_outlined, activeIcon: Icons.home, label: 'HOME'),
    NavBarItem(icon: Icons.fitness_center_outlined, activeIcon: Icons.fitness_center, label: 'WORKOUTS'),
    NavBarItem(icon: Icons.calendar_month_outlined, activeIcon: Icons.calendar_month, label: 'TIMETABLE'),
    NavBarItem(icon: Icons.location_on_outlined, activeIcon: Icons.location_on, label: 'FIND GYM'),
    NavBarItem(icon: Icons.person_outline, activeIcon: Icons.person, label: 'PROFILE'),
  ];

  const FloatingNavBar({super.key, required this.currentIndex, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      minimum: const EdgeInsets.fromLTRB(28, 0, 28, 14),
      child: SizedBox(
        height: _barHeight + _overflow,
        child: LayoutBuilder(
          builder: (context, constraints) {
            final itemWidth = constraints.maxWidth / items.length;
            final bubbleLeft = itemWidth * currentIndex + (itemWidth - _bubbleSize) / 2;

            return Stack(
              clipBehavior: Clip.none,
              children: [
                // The bar itself, sitting at the bottom of the reserved space.
                Positioned(
                  left: 0,
                  right: 0,
                  bottom: 0,
                  height: _barHeight,
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(_barHeight / 2),
                    child: BackdropFilter(
                      filter: ImageFilter.blur(sigmaX: 18, sigmaY: 18),
                      child: Container(
                        decoration: BoxDecoration(
                          color: AppColors.bgSecondary.withOpacity(0.88),
                          borderRadius: BorderRadius.circular(_barHeight / 2),
                          border: Border.all(color: AppColors.border),
                          boxShadow: const [
                            BoxShadow(color: AppColors.cardShadow, blurRadius: 24, offset: Offset(0, 10)),
                          ],
                        ),
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
                  ),
                ),
                // The floating, glowing bubble for the active tab.
                AnimatedPositioned(
                  duration: const Duration(milliseconds: 380),
                  curve: Curves.easeOutBack,
                  left: bubbleLeft,
                  top: 0,
                  width: _bubbleSize,
                  height: _bubbleSize,
                  child: IgnorePointer(
                    child: _DockBubble(key: ValueKey(currentIndex), item: items[currentIndex]),
                  ),
                ),
              ],
            );
          },
        ),
      ),
    ).animate().fadeIn(duration: 450.ms).slideY(begin: 0.6, end: 0, curve: Curves.easeOutCubic);
  }
}

class _DockBubble extends StatelessWidget {
  final NavBarItem item;
  const _DockBubble({super.key, required this.item});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: _bubbleSize,
      height: _bubbleSize,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: AppColors.bgPrimary,
        border: Border.all(color: AppColors.accent, width: 3),
        boxShadow: const [BoxShadow(color: AppColors.shadowAccent, blurRadius: 16, spreadRadius: 1)],
      ),
      alignment: Alignment.center,
      child: Icon(item.activeIcon, color: AppColors.accent, size: 24),
    )
        .animate()
        .scale(begin: const Offset(0.4, 0.4), curve: Curves.elasticOut, duration: 550.ms)
        .fadeIn(duration: 200.ms);
  }
}

class _DockSlot extends StatefulWidget {
  final NavBarItem item;
  final bool selected;
  final VoidCallback onTap;

  const _DockSlot({required this.item, required this.selected, required this.onTap});

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
            // Reserves the icon's footprint but hides it once it's "lifted"
            // into the floating bubble above, so nothing doubles up.
            AnimatedOpacity(
              duration: const Duration(milliseconds: 180),
              opacity: widget.selected ? 0 : 1,
              child: Icon(widget.item.icon, color: AppColors.textMuted, size: 22),
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
