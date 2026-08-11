import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppColors {
  static const Color bgPrimary = Color(0xFF111111);
  static const Color bgSecondary = Color(0xFF1A1A1A);
  static const Color bgCard = Color(0xFF1E1E1E);
  static const Color bgCardHover = Color(0xFF252525);
  
  static const Color accent = Color(0xFFC8F000); // Electric Lime
  static const Color accentDark = Color(0xFF9AB800);
  static const Color accentGlow = Color(0x4DC8F000);
  
  static const Color textPrimary = Color(0xFFFFFFFF);
  static const Color textSecondary = Color(0xFFB0B0B0);
  static const Color textMuted = Color(0xFF6B6B6B);
  
  static const Color border = Color(0x1AFFFFFF);
  static const Color borderAccent = Color(0x66C8F000);
  
  static const Color shadowAccent = Color(0x26C8F000);
}

class SlantedClipper extends CustomClipper<Path> {
  final double slantWidth;

  SlantedClipper({this.slantWidth = 10.0});

  @override
  Path getClip(Size size) {
    Path path = Path();
    path.moveTo(slantWidth, 0);
    path.lineTo(size.width, 0);
    path.lineTo(size.width - slantWidth, size.height);
    path.lineTo(0, size.height);
    path.close();
    return path;
  }

  @override
  bool shouldReclip(covariant CustomClipper<Path> oldClipper) => false;
}

class AppTheme {
  static ThemeData get darkTheme {
    return ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: AppColors.bgPrimary,
      primaryColor: AppColors.accent,
      colorScheme: const ColorScheme.dark(
        primary: AppColors.accent,
        secondary: AppColors.accentDark,
        surface: AppColors.bgCard,
        background: AppColors.bgPrimary,
      ),
      fontFamily: GoogleFonts.inter().fontFamily,
      textTheme: TextTheme(
        displayLarge: GoogleFonts.oswald(
          fontSize: 32,
          fontWeight: FontWeight.bold,
          color: AppColors.textPrimary,
          letterSpacing: 1.5,
        ),
        displayMedium: GoogleFonts.oswald(
          fontSize: 24,
          fontWeight: FontWeight.bold,
          color: AppColors.textPrimary,
          letterSpacing: 1.2,
        ),
        titleLarge: GoogleFonts.oswald(
          fontSize: 20,
          fontWeight: FontWeight.w600,
          color: AppColors.textPrimary,
          letterSpacing: 1.0,
        ),
        bodyLarge: GoogleFonts.inter(
          fontSize: 16,
          fontWeight: FontWeight.normal,
          color: AppColors.textPrimary,
        ),
        bodyMedium: GoogleFonts.inter(
          fontSize: 14,
          fontWeight: FontWeight.normal,
          color: AppColors.textSecondary,
        ),
      ),
    );
  }
}
