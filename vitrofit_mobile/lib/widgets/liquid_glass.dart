import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// A flat, solid card surface - the shared building block for every card,
/// bar, sheet, and button-ish container in the app.
class LiquidGlassContainer extends StatelessWidget {
  final Widget child;
  final BorderRadius borderRadius;
  final EdgeInsetsGeometry? padding;
  final Color tint;
  final double tintOpacity;
  final double blurSigma;
  final Border? border;
  final List<BoxShadow>? boxShadow;
  final bool blur;

  const LiquidGlassContainer({
    super.key,
    required this.child,
    this.borderRadius = const BorderRadius.all(Radius.circular(20)),
    this.padding,
    this.tint = AppColors.bgCard,
    this.tintOpacity = 0.55,
    this.blurSigma = 16,
    this.border,
    this.boxShadow,
    this.blur = true,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: tint,
        borderRadius: borderRadius,
        border: border ?? Border.all(color: AppColors.border, width: 1.2),
        boxShadow:
            boxShadow ??
            const [
              BoxShadow(
                color: AppColors.cardShadow,
                blurRadius: 18,
                offset: Offset(0, 8),
              ),
            ],
      ),
      child: ClipRRect(borderRadius: borderRadius, child: child),
    );
  }
}

/// A drop-in solid-card replacement for the app's common
/// `Container(color: bgCard, border: Border.all(color: border))` card pattern.
class LiquidGlassCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry padding;
  final double borderRadius;
  final Color tint;
  final Border? border;
  final bool blur;

  const LiquidGlassCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(16),
    this.borderRadius = 14,
    this.tint = AppColors.bgCard,
    this.border,
    this.blur = false,
  });

  @override
  Widget build(BuildContext context) {
    return LiquidGlassContainer(
      borderRadius: BorderRadius.circular(borderRadius),
      padding: padding,
      tint: tint,
      tintOpacity: 0.5,
      blurSigma: 18,
      border: border,
      blur: blur,
      child: child,
    );
  }
}
