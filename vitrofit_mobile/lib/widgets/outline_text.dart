import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/app_theme.dart';

class OutlineText extends StatelessWidget {
  final String text;
  final double fontSize;
  final Color strokeColor;
  final double strokeWidth;

  const OutlineText({
    super.key,
    required this.text,
    this.fontSize = 28,
    this.strokeColor = AppColors.textPrimary,
    this.strokeWidth = 1.5,
  });

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        // Stroke
        Text(
          text.toUpperCase(),
          style: GoogleFonts.oswald(
            fontSize: fontSize,
            fontWeight: FontWeight.w800,
            letterSpacing: 2.0,
            foreground: Paint()
              ..style = PaintingStyle.stroke
              ..strokeWidth = strokeWidth
              ..color = strokeColor.withOpacity(0.8),
          ),
        ),
        // Fill (Transparent/Empty to achieve outlined effect)
        Text(
          text.toUpperCase(),
          style: GoogleFonts.oswald(
            fontSize: fontSize,
            fontWeight: FontWeight.w800,
            letterSpacing: 2.0,
            color: Colors.transparent,
          ),
        ),
      ],
    );
  }
}
