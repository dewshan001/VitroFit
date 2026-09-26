import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/app_theme.dart';

class BadgeChip extends StatelessWidget {
  final String label;
  final bool isAccent;
  final Color? color;

  const BadgeChip({
    super.key,
    required this.label,
    this.isAccent = true,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    final fillColor = color ?? (isAccent ? AppColors.accent : AppColors.bgCardHover);
    final useDarkText = color != null || isAccent;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: fillColor,
        borderRadius: BorderRadius.circular(4),
        boxShadow: (isAccent || color != null)
            ? [
                BoxShadow(
                  color: fillColor.withOpacity(0.3),
                  blurRadius: 8,
                  offset: const Offset(0, 2),
                )
              ]
            : [],
      ),
      child: Text(
        label.toUpperCase(),
        style: GoogleFonts.oswald(
          fontSize: 11,
          fontWeight: FontWeight.bold,
          letterSpacing: 1.0,
          color: useDarkText ? AppColors.bgPrimary : AppColors.textPrimary,
        ),
      ),
    );
  }
}
