import 'package:flutter/material.dart';
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
          scale: _isPressed ? 0.96 : 1.0,
          duration: const Duration(milliseconds: 120),
          child: Container(
            decoration: BoxDecoration(
              boxShadow: widget.isSecondary || _isPressed
                  ? []
                  : [
                      BoxShadow(
                        color: AppColors.accent.withOpacity(0.35),
                        blurRadius: 16,
                        spreadRadius: 1,
                        offset: const Offset(0, 4),
                      ),
                    ],
            ),
            child: ClipPath(
              clipper: SlantedClipper(slantWidth: 8),
              child: Container(
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
                child: widget.isLoading
                    ? SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(
                          strokeWidth: 2.2,
                          valueColor: AlwaysStoppedAnimation<Color>(
                            widget.isSecondary ? AppColors.accent : AppColors.bgPrimary,
                          ),
                        ),
                      )
                    : Row(
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
    );
  }
}
