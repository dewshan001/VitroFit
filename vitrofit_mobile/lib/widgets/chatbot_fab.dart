import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../screens/chatbot_screen.dart';
import '../theme/app_theme.dart';
import 'liquid_glass.dart';

/// Global entry point into VitroBot, visible from every tab - mirrors the
/// website's floating action button that's mounted once at the app root.
class ChatbotFab extends StatelessWidget {
  const ChatbotFab({super.key});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () => ChatbotScreen.show(context),
      child: SizedBox(
        width: 58,
        height: 58,
        child: Stack(
          alignment: Alignment.center,
          clipBehavior: Clip.none,
          children: [
            // Pulse rings
            ...List.generate(2, (i) {
              return Container(
                    width: 58,
                    height: 58,
                    decoration: const BoxDecoration(
                      shape: BoxShape.circle,
                      color: AppColors.accent,
                    ),
                  )
                  .animate(onPlay: (c) => c.repeat(), delay: (i * 900).ms)
                  .scaleXY(
                    begin: 1.0,
                    end: 1.6,
                    duration: 1800.ms,
                    curve: Curves.easeOut,
                  )
                  .fadeOut(
                    duration: 1800.ms,
                    curve: Curves.easeOut,
                    begin: 0.35,
                  );
            }),
            SizedBox(
              width: 56,
              height: 56,
              child: LiquidGlassContainer(
                borderRadius: BorderRadius.circular(28),
                tint: AppColors.bgPrimary,
                tintOpacity: 0.65,
                blur: false,
                border: Border.all(color: AppColors.accent, width: 2.5),
                boxShadow: const [
                  BoxShadow(
                    color: AppColors.shadowAccent,
                    blurRadius: 16,
                    spreadRadius: 2,
                  ),
                ],
                child: const Center(
                  child: Icon(
                    Icons.smart_toy_outlined,
                    color: AppColors.accent,
                    size: 26,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
