import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/app_theme.dart';
import 'liquid_glass.dart';

/// Small building blocks shared by the Fitness, Diet and Time agent screens so
/// they match the Gym tab's look without each re-declaring the same styling.

class AgentHeader extends StatelessWidget {
  final String eyebrow;
  final String title;
  final String? subtitle;

  const AgentHeader({
    super.key,
    required this.eyebrow,
    required this.title,
    this.subtitle,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          eyebrow.toUpperCase(),
          style: GoogleFonts.oswald(
            fontSize: 12,
            fontWeight: FontWeight.bold,
            letterSpacing: 2.2,
            color: AppColors.accent,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          title,
          style: GoogleFonts.oswald(
            fontSize: 28,
            fontWeight: FontWeight.w900,
            height: 1.1,
            color: AppColors.textPrimary,
          ),
        ),
        if (subtitle != null) ...[
          const SizedBox(height: 6),
          Text(
            subtitle!,
            style: GoogleFonts.inter(
              fontSize: 13,
              color: AppColors.textSecondary,
              height: 1.4,
            ),
          ),
        ],
      ],
    );
  }
}

/// A flat card surface with optional accent border.
class AgentCard extends StatelessWidget {
  final Widget child;
  final bool accent;
  final EdgeInsetsGeometry padding;

  const AgentCard({
    super.key,
    required this.child,
    this.accent = false,
    this.padding = const EdgeInsets.all(16),
  });

  @override
  Widget build(BuildContext context) {
    return LiquidGlassContainer(
      borderRadius: BorderRadius.circular(16),
      padding: padding,
      blur: false,
      border: Border.all(
        color: accent ? AppColors.borderAccent : AppColors.border,
        width: 1.2,
      ),
      child: SizedBox(width: double.infinity, child: child),
    );
  }
}

class SectionTitle extends StatelessWidget {
  final String text;
  const SectionTitle(this.text, {super.key});

  @override
  Widget build(BuildContext context) {
    return Text(
      text.toUpperCase(),
      style: GoogleFonts.oswald(
        fontSize: 15,
        fontWeight: FontWeight.bold,
        letterSpacing: 1.0,
        color: AppColors.textPrimary,
      ),
    );
  }
}

/// An inline error or notice banner.
class AgentBanner extends StatelessWidget {
  final String message;
  final bool isError;
  final IconData? icon;

  const AgentBanner({
    super.key,
    required this.message,
    this.isError = false,
    this.icon,
  });

  @override
  Widget build(BuildContext context) {
    final color = isError ? AppColors.error : AppColors.accent;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withValues(alpha: 0.45)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            icon ?? (isError ? Icons.error_outline : Icons.info_outline),
            color: color,
            size: 18,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              message,
              style: GoogleFonts.inter(
                fontSize: 12.5,
                height: 1.4,
                color: isError ? AppColors.error : AppColors.textPrimary,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// A selectable pill used for single/multi choice groups.
class SelectChip extends StatelessWidget {
  final String label;
  final String? sub;
  final bool selected;
  final VoidCallback? onTap;

  const SelectChip({
    super.key,
    required this.label,
    required this.selected,
    required this.onTap,
    this.sub,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: selected ? AppColors.accent : AppColors.bgCard,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: selected ? AppColors.accent : AppColors.border,
          ),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label,
              style: GoogleFonts.oswald(
                fontSize: 13,
                fontWeight: FontWeight.bold,
                color: selected ? AppColors.bgPrimary : AppColors.textPrimary,
              ),
            ),
            if (sub != null)
              Text(
                sub!,
                style: GoogleFonts.inter(
                  fontSize: 10.5,
                  color: selected
                      ? AppColors.bgPrimary.withValues(alpha: 0.75)
                      : AppColors.textMuted,
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class FieldLabel extends StatelessWidget {
  final String text;
  const FieldLabel(this.text, {super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Text(
        text.toUpperCase(),
        style: GoogleFonts.oswald(
          fontSize: 13,
          fontWeight: FontWeight.bold,
          letterSpacing: 1.0,
          color: AppColors.textPrimary,
        ),
      ),
    );
  }
}

/// Themed checkbox row.
class CheckRow extends StatelessWidget {
  final String label;
  final bool value;
  final ValueChanged<bool>? onChanged;

  const CheckRow({
    super.key,
    required this.label,
    required this.value,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(8),
      onTap: onChanged == null ? null : () => onChanged!(!value),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: 28,
              height: 28,
              child: Checkbox(
                value: value,
                onChanged: onChanged == null ? null : (v) => onChanged!(v ?? false),
                activeColor: AppColors.accent,
                checkColor: AppColors.bgPrimary,
                side: const BorderSide(color: AppColors.textMuted),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.only(top: 5),
                child: Text(
                  label,
                  style: GoogleFonts.inter(
                    fontSize: 13,
                    height: 1.35,
                    color: AppColors.textPrimary,
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

/// Themed dropdown used in agent forms.
class AgentDropdown<T> extends StatelessWidget {
  final T value;
  final List<DropdownMenuItem<T>> items;
  final ValueChanged<T?>? onChanged;

  const AgentDropdown({
    super.key,
    required this.value,
    required this.items,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.border),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<T>(
          isExpanded: true,
          value: value,
          dropdownColor: AppColors.bgCard,
          style: GoogleFonts.inter(color: AppColors.textPrimary, fontSize: 14),
          icon: const Icon(Icons.arrow_drop_down, color: AppColors.accent),
          items: items,
          onChanged: onChanged,
        ),
      ),
    );
  }
}

/// Plain multi-line text input matching [VitroTextField]'s styling.
class AgentTextArea extends StatelessWidget {
  final TextEditingController controller;
  final String hint;
  final int maxLength;
  final int minLines;
  final bool enabled;

  const AgentTextArea({
    super.key,
    required this.controller,
    required this.hint,
    this.maxLength = 300,
    this.minLines = 2,
    this.enabled = true,
  });

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      enabled: enabled,
      minLines: minLines,
      maxLines: minLines + 3,
      maxLength: maxLength,
      style: GoogleFonts.inter(color: AppColors.textPrimary, fontSize: 14),
      decoration: InputDecoration(
        hintText: hint,
        hintStyle: GoogleFonts.inter(color: AppColors.textMuted, fontSize: 13),
        filled: true,
        fillColor: AppColors.bgCard,
        counterStyle: GoogleFonts.inter(color: AppColors.textMuted, fontSize: 10),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: AppColors.border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: AppColors.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: AppColors.accent, width: 1.5),
        ),
      ),
    );
  }
}

/// A modest outlined action button for secondary/destructive actions.
class AgentTextButton extends StatelessWidget {
  final String label;
  final IconData? icon;
  final VoidCallback? onPressed;
  final bool danger;

  const AgentTextButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.icon,
    this.danger = false,
  });

  @override
  Widget build(BuildContext context) {
    final color = danger ? AppColors.error : AppColors.accent;
    return TextButton.icon(
      onPressed: onPressed,
      icon: Icon(icon ?? Icons.arrow_forward, size: 16, color: onPressed == null ? AppColors.textMuted : color),
      label: Text(
        label.toUpperCase(),
        style: GoogleFonts.oswald(
          fontWeight: FontWeight.bold,
          letterSpacing: 1.0,
          fontSize: 13,
          color: onPressed == null ? AppColors.textMuted : color,
        ),
      ),
    );
  }
}

Future<bool> confirmDialog(
  BuildContext context, {
  required String title,
  required String message,
  String confirmLabel = 'CONFIRM',
  bool danger = false,
}) async {
  final color = danger ? AppColors.error : AppColors.accent;
  final result = await showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      backgroundColor: AppColors.bgCard,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: color),
      ),
      title: Text(
        title,
        style: GoogleFonts.oswald(fontWeight: FontWeight.bold, color: color),
      ),
      content: Text(
        message,
        style: GoogleFonts.inter(color: AppColors.textSecondary),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context, false),
          child: Text(
            'CANCEL',
            style: GoogleFonts.oswald(color: AppColors.textMuted),
          ),
        ),
        TextButton(
          onPressed: () => Navigator.pop(context, true),
          child: Text(
            confirmLabel,
            style: GoogleFonts.oswald(color: color, fontWeight: FontWeight.bold),
          ),
        ),
      ],
    ),
  );
  return result == true;
}

void showAgentSnack(BuildContext context, String message, {bool error = false}) {
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(
      SnackBar(
        backgroundColor: error ? AppColors.error : AppColors.bgCard,
        content: Text(
          message,
          style: GoogleFonts.inter(
            color: error ? AppColors.bgPrimary : AppColors.textPrimary,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
    );
}
