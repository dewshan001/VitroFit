import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../models/timetable_slot.dart';
import '../models/user_profile.dart';
import '../state/app_state.dart';
import '../theme/app_theme.dart';
import '../widgets/badge_chip.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final appState = context.watch<AppState>();
    final user = appState.currentUser;

    if (user == null) {
      // The router keeps unauthenticated users off /main entirely, but guard
      // defensively in case of a brief state transition mid-logout.
      return const SizedBox.shrink();
    }

    return RefreshIndicator(
      color: AppColors.accent,
      backgroundColor: AppColors.bgCard,
      onRefresh: () => appState.refreshAll(),
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(parent: BouncingScrollPhysics()),
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildProfileBanner(user),
            const SizedBox(height: 24),
            Text(
              "MY UPCOMING SESSIONS",
              style: GoogleFonts.oswald(fontSize: 16, fontWeight: FontWeight.bold, letterSpacing: 1.0, color: AppColors.textMuted),
            ),
            const SizedBox(height: 10),
            _buildUpcomingSessions(context, appState),
            const SizedBox(height: 24),
            Text(
              "ACCOUNT & PREFERENCES",
              style: GoogleFonts.oswald(fontSize: 16, fontWeight: FontWeight.bold, letterSpacing: 1.0, color: AppColors.textMuted),
            ),
            const SizedBox(height: 10),
            _buildSettingOption(context, Icons.person_outline, "Personal Details", () => context.push('/main/personal-details')),
            _buildSettingOption(context, Icons.lock_outline, "Change Password", () => context.push('/main/change-password')),
            _buildSettingOption(context, Icons.credit_card, "Payment & Billing", () => context.push('/main/billing')),
            _buildSettingOption(context, Icons.notifications_none, "Notification Settings", () => context.push('/main/notifications')),
            _buildSettingOption(context, Icons.help_outline, "Customer Support", () => context.push('/main/support')),
            _buildSettingOption(context, Icons.info_outline, "About VitroFit", () => context.push('/main/about')),
            _buildSettingOption(context, Icons.logout, "Sign Out", () => appState.logout(), isDanger: false),
            _buildSettingOption(context, Icons.delete_forever_outlined, "Delete Account", () => _confirmDeleteAccount(context, appState), isDanger: true),
            const SizedBox(height: 30),
          ],
        ),
      ),
    );
  }

  Widget _buildProfileBanner(UserProfile user) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.borderAccent),
        boxShadow: const [BoxShadow(color: AppColors.shadowAccent, blurRadius: 16)],
      ),
      child: Row(
        children: [
          Container(
            width: 64,
            height: 64,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: AppColors.accent, width: 2),
              color: AppColors.bgSecondary,
              image: user.profileImageUrl != null
                  ? DecorationImage(image: NetworkImage(user.profileImageUrl!), fit: BoxFit.cover)
                  : null,
            ),
            child: user.profileImageUrl == null
                ? Center(
                    child: Text(
                      user.initials,
                      style: GoogleFonts.oswald(fontSize: 22, fontWeight: FontWeight.bold, color: AppColors.accent),
                    ),
                  )
                : null,
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  crossAxisAlignment: WrapCrossAlignment.center,
                  spacing: 8,
                  runSpacing: 4,
                  children: [
                    Text(
                      user.fullName,
                      style: GoogleFonts.oswald(fontSize: 22, fontWeight: FontWeight.bold, color: AppColors.textPrimary),
                    ),
                    if (user.role != UserRole.user) BadgeChip(label: user.role.name.toUpperCase()),
                  ],
                ),
                const SizedBox(height: 2),
                Text(user.email, style: GoogleFonts.inter(fontSize: 12, color: AppColors.textMuted)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildUpcomingSessions(BuildContext context, AppState appState) {
    if (appState.timetableLoading && appState.timetableSlots.isEmpty) {
      return Text("Loading your timetable…", style: GoogleFonts.inter(color: AppColors.textMuted));
    }
    if (appState.timetableSlots.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(color: AppColors.bgCard, borderRadius: BorderRadius.circular(10), border: Border.all(color: AppColors.border)),
        child: Row(
          children: [
            const Icon(Icons.event_note, color: AppColors.textMuted),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                "No sessions yet. Add workouts to your timetable from the WORKOUTS tab.",
                style: GoogleFonts.inter(fontSize: 12.5, color: AppColors.textSecondary),
              ),
            ),
          ],
        ),
      );
    }

    final upcoming = appState.timetableSlots.take(3).toList();
    return Column(
      children: upcoming
          .map((slot) => _buildSessionItem(slot))
          .toList()
          .animate(interval: 60.ms)
          .fadeIn(duration: 300.ms)
          .slideX(begin: 0.08, end: 0, curve: Curves.easeOut),
    );
  }

  Widget _buildSessionItem(TimetableSlot slot) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: AppColors.bgCard, borderRadius: BorderRadius.circular(10), border: Border.all(color: AppColors.border)),
      child: Row(
        children: [
          const Icon(Icons.event_available, color: AppColors.accent, size: 24),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(slot.title, style: GoogleFonts.oswald(fontSize: 16, fontWeight: FontWeight.bold, color: AppColors.textPrimary)),
                Text(
                  "${slot.day.label} • ${slot.startTime.label} - ${slot.endTime.label}",
                  style: GoogleFonts.inter(fontSize: 12, color: AppColors.textSecondary),
                ),
              ],
            ),
          ),
          Text(slot.workoutCategory, style: GoogleFonts.inter(fontSize: 11, color: AppColors.accent, fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }

  Widget _buildSettingOption(BuildContext context, IconData icon, String label, VoidCallback onTap, {bool isDanger = false}) {
    final color = isDanger ? AppColors.error : AppColors.textPrimary;
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(color: AppColors.bgCard, borderRadius: BorderRadius.circular(10), border: Border.all(color: AppColors.border)),
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(10),
        child: ListTile(
          onTap: onTap,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          leading: Icon(icon, color: color, size: 20),
          title: Text(label, style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w500, color: color)),
          trailing: Icon(Icons.arrow_forward_ios, size: 14, color: isDanger ? AppColors.error : AppColors.textMuted),
        ),
      ),
    );
  }

  Future<void> _confirmDeleteAccount(BuildContext context, AppState appState) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColors.bgCard,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16), side: const BorderSide(color: AppColors.error)),
        title: Text("DELETE ACCOUNT?", style: GoogleFonts.oswald(fontWeight: FontWeight.bold, color: AppColors.error)),
        content: Text(
          "This permanently deletes your VitroFit account and timetable. This cannot be undone.",
          style: GoogleFonts.inter(color: AppColors.textSecondary),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text("CANCEL", style: GoogleFonts.oswald(color: AppColors.textMuted)),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text("DELETE", style: GoogleFonts.oswald(color: AppColors.error, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        await appState.deleteAccount();
      } catch (e) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(backgroundColor: AppColors.error, content: Text(e.toString())),
          );
        }
      }
    }
  }
}
