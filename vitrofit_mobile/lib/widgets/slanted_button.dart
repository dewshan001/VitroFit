import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/app_theme.dart';

class SlantedButton extends StatefulWidget {
  final String text;
  final VoidCallback onPressed;
  final bool isSecondary;
  final IconData? icon;
  final double paddingVertical;
  final double paddingHorizontal;
  final bool isLoading;
  final bool isDisabled;

  const SlantedButton({
    super.key,
    required this.text,
    required this.onPressed,
    this.isSecondary = false,
    this.icon,
    this.paddingVertical = 14,
    this.paddingHorizontal = 28,
    this.isLoading = false,
    this.isDisabled = false,
  });

  @override
  State<SlantedButton> createState() => _SlantedButtonState();
}

class _SlantedButtonState extends State<SlantedButton> {
  bool _isPressed = false;

  bool get _interactive => !widget.isLoading && !widget.isDisabled;

  @override
  Widget build(BuildContext context) {
    return Opacity(
      opacity: widget.isDisabled ? 0.5 : 1.0,
      child: GestureDetector(
        onTapDown: _interactive ? (_) => setState(() => _isPressed = true) : null,
        onTapUp: _interactive
            ? (_) {
                setState(() => _isPressed = false);
                widget.onPressed();
              }
            : null,
        onTapCancel: _interactive ? () => setState(() => _isPressed = false) : null,
        child: AnimatedScale(
          scale: _isPressed ? 0.96 : (widget.isLoading ? 0.99 : 1.0),
          duration: const Duration(milliseconds: 120),
          curve: Curves.easeOut,
          child: Container(
            decoration: BoxDecoration(
              boxShadow: widget.isSecondary || _isPressed
                  ? []
                  : [
                      BoxShadow(
                        color: AppColors.accent.withOpacity(widget.isLoading ? 0.5 : 0.35),
                        blurRadius: widget.isLoading ? 22 : 16,
                        spreadRadius: 1,
                        offset: const Offset(0, 4),
                      ),
                    ],
            ),
            child: ClipPath(
              clipper: SlantedClipper(slantWidth: 8),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                padding: EdgeInsets.symmetric(
                  vertical: widget.paddingVertical,
                  horizontal: widget.paddingHorizontal,
                ),
                decoration: BoxDecoration(
                  color: widget.isSecondary
                      ? Colors.transparent
                      : AppColors.accent,
                  border: widget.isSecondary
                      ? Border.all(
                          color: AppColors.accent,
                          width: 2,
                        )
                      : null,
                ),
                child: AnimatedSwitcher(
                  duration: const Duration(milliseconds: 280),
                  switchInCurve: Curves.easeOutBack,
                  switchOutCurve: Curves.easeIn,
                  transitionBuilder: (child, animation) => FadeTransition(
                    opacity: animation,
                    child: ScaleTransition(scale: animation, child: child),
                  ),
                  child: widget.isLoading
                      ? Row(
                          key: const ValueKey('loading'),
                          mainAxisSize: MainAxisSize.min,
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(
                                strokeWidth: 2.2,
                                valueColor: AlwaysStoppedAnimation<Color>(
                                  widget.isSecondary ? AppColors.accent : AppColors.bgPrimary,
                                ),
                              ),
                            ),
                            const SizedBox(width: 10),
                            Text(
                              "PLEASE WAIT",
                              style: GoogleFonts.oswald(
                                color: widget.isSecondary ? AppColors.accent : AppColors.bgPrimary,
                                fontWeight: FontWeight.bold,
                                fontSize: 15,
                                letterSpacing: 1.5,
                              ),
                            ),
                          ],
                        ).animate(onPlay: (c) => c.repeat(reverse: true)).fadeOut(
                            duration: 700.ms,
                            curve: Curves.easeInOut,
                            begin: 1.0,
                          )
                      : Row(
                          key: const ValueKey('content'),
                          mainAxisSize: MainAxisSize.min,
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(
                              widget.text.toUpperCase(),
                              style: GoogleFonts.oswald(
                                color: widget.isSecondary
                                    ? AppColors.accent
                                    : AppColors.bgPrimary,
                                fontWeight: FontWeight.bold,
                                fontSize: 15,
                                letterSpacing: 1.5,
                              ),
                            ),
                            if (widget.icon != null) ...[
                              const SizedBox(width: 8),
                              Icon(
                                widget.icon,
                                size: 18,
                                color: widget.isSecondary
                                    ? AppColors.accent
                                    : AppColors.bgPrimary,
                              ),
                            ],
                          ],
                        ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
