import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../theme/app_theme.dart';

/// Reusable settings sub-screen for informational destinations
/// (billing, support) or simple local toggle preferences (notifications).
class InfoScreen extends StatefulWidget {
  final String title;
  final IconData icon;
  final String body;
  final bool isTogglesDemo;

  const InfoScreen({
    super.key,
    required this.title,
    required this.icon,
    required this.body,
    this.isTogglesDemo = false,
  });

  @override
  State<InfoScreen> createState() => _InfoScreenState();
}

class _InfoScreenState extends State<InfoScreen> {
  bool _classReminders = true;
  bool _newWorkouts = true;
  bool _productUpdates = false;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgPrimary,
      appBar: AppBar(
        backgroundColor: AppColors.bgPrimary,
        elevation: 0,
        title: Text(widget.title, style: GoogleFonts.oswald(fontWeight: FontWeight.bold, letterSpacing: 1)),
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: AppColors.bgCard,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: AppColors.border),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(widget.icon, color: AppColors.accent, size: 28),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Text(
                      widget.body,
                      style: GoogleFonts.inter(fontSize: 13.5, height: 1.5, color: AppColors.textSecondary),
                    ),
                  ),
                ],
              ),
            ),
            if (widget.isTogglesDemo) ...[
              const SizedBox(height: 20),
              _toggleRow("Class reminders", "Alerts before your scheduled sessions", _classReminders,
                  (v) => setState(() => _classReminders = v)),
              _toggleRow("New workouts", "When the studio adds a new workout to the catalog", _newWorkouts,
                  (v) => setState(() => _newWorkouts = v)),
              _toggleRow("Product updates", "News and announcements from VitroFit", _productUpdates,
                  (v) => setState(() => _productUpdates = v)),
            ],
          ],
        ),
      ),
    );
  }

  Widget _toggleRow(String title, String subtitle, bool value, ValueChanged<bool> onChanged) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.border),
      ),
      child: SwitchListTile(
        value: value,
        onChanged: onChanged,
        activeColor: AppColors.accent,
        activeTrackColor: AppColors.accentGlow,
        title: Text(title, style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
        subtitle: Text(subtitle, style: GoogleFonts.inter(fontSize: 11.5, color: AppColors.textMuted)),
        contentPadding: EdgeInsets.zero,
      ),
    );
  }
}
