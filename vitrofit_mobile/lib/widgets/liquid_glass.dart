import 'dart:ui';

import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// A reusable "liquid glass" material: heavy blur, translucent fill, a soft
/// refractive gradient border, and a diagonal specular sheen near the top
/// edge - the shared building block for every floating/glassy surface in the
/// app (nav bar, app bar, FAB, cards, sheets, outlined buttons).
class LiquidGlassContainer extends StatelessWidget {
  final Widget child;
  final BorderRadius borderRadius;
  final EdgeInsetsGeometry? padding;
  final Color tint;
  final double tintOpacity;
  final double blurSigma;
  final Border? border;
  final List<BoxShadow>? boxShadow;

  /// Whether to apply a real [BackdropFilter] blur. BackdropFilter is
  /// expensive to composite - fine for a handful of persistent overlays
  /// (app bar, nav dock, FAB, sheets), but repeating it across many list/grid
  /// items causes visible jank. Widgets rendered per-item in a scrollable
  /// list should pass `blur: false` to get the same translucent/gradient
  /// look without the per-frame blur cost.
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
    final content = Container(
      padding: padding,
      decoration: BoxDecoration(
        color: tint.withOpacity(blur ? tintOpacity : tintOpacity + 0.2),
        borderRadius: borderRadius,
        border: border ?? Border.all(color: AppColors.border, width: 1.2),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Colors.white.withOpacity(0.07),
            tint.withOpacity(tintOpacity),
            tint.withOpacity(tintOpacity),
          ],
          stops: const [0.0, 0.35, 1.0],
        ),
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
      child: Stack(
        children: [
          // Diagonal specular sheen - the "liquid" highlight catching light.
          Positioned.fill(
            child: IgnorePointer(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  borderRadius: borderRadius,
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      Colors.white.withOpacity(0.10),
                      Colors.white.withOpacity(0.0),
                    ],
                    stops: const [0.0, 0.45],
                  ),
                ),
              ),
            ),
          ),
          child,
        ],
      ),
    );

    if (!blur) {
      return ClipRRect(borderRadius: borderRadius, child: content);
    }

    return ClipRRect(
      borderRadius: borderRadius,
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: blurSigma, sigmaY: blurSigma),
        child: content,
      ),
    );
  }
}

/// A drop-in glass replacement for the app's common
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
