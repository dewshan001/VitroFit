import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/app_theme.dart';

class BadgeChip extends StatelessWidget {
  final String label;
  final bool isAccent;

  const BadgeChip({
    super.key,
    required this.label,
    this.isAccent = true,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: isAccent ? AppColors.accent : AppColors.bgCardHover,
        borderRadius: BorderRadius.circular(4),
        boxShadow: isAccent
            ? [
                BoxShadow(
                  color: AppColors.accent.withOpacity(0.3),
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
          color: isAccent ? AppColors.bgPrimary : AppColors.textPrimary,
        ),
      ),
    );
  }
}
