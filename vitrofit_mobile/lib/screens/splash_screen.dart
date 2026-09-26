import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/app_theme.dart';

/// Shown only while AppState resolves whether a stored session is still
/// valid (a single `/auth/me` call) before the router redirects to
/// `/auth` or `/main`.
class SplashScreen extends StatelessWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgPrimary,
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 14,
              height: 40,
              decoration: BoxDecoration(
                color: AppColors.accent,
                borderRadius: BorderRadius.circular(3),
                boxShadow: const [BoxShadow(color: AppColors.shadowAccent, blurRadius: 20)],
              ),
            ).animate(onPlay: (c) => c.repeat(reverse: true)).scaleY(
                  begin: 0.6,
                  end: 1.0,
                  duration: 700.ms,
                  curve: Curves.easeInOut,
                ),
            const SizedBox(height: 20),
            Text(
              "VITROFIT",
              style: GoogleFonts.oswald(
                fontSize: 22,
                fontWeight: FontWeight.w900,
                letterSpacing: 3,
                color: AppColors.textPrimary,
              ),
            ).animate().fadeIn(duration: 400.ms),
          ],
        ),
      ),
    );
  }
}
