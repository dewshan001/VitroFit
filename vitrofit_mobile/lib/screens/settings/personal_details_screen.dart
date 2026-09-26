import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import '../../api/api_exception.dart';
import '../../state/app_state.dart';
import '../../theme/app_theme.dart';

/// The backend only exposes name/email/phone as read-only via GET /auth/me
/// (no update-profile endpoint exists) — this screen shows those fields and
/// lets the user change their profile photo, which IS a real backend action.
class PersonalDetailsScreen extends StatefulWidget {
  const PersonalDetailsScreen({super.key});

  @override
  State<PersonalDetailsScreen> createState() => _PersonalDetailsScreenState();
}

class _PersonalDetailsScreenState extends State<PersonalDetailsScreen> {
  bool _uploading = false;

  Future<void> _pickAndUploadPhoto() async {
    final picker = ImagePicker();
    final picked = await picker.pickImage(source: ImageSource.gallery, maxWidth: 1024, imageQuality: 85);
    if (picked == null || !mounted) return;

    final appState = context.read<AppState>();
    setState(() => _uploading = true);
    try {
      await appState.uploadPhoto(picked.path);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            backgroundColor: AppColors.success,
            content: Text("Profile photo updated.", style: GoogleFonts.inter(fontWeight: FontWeight.bold)),
          ),
        );
      }
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(backgroundColor: AppColors.error, content: Text(e.message)),
        );
      }
    } finally {
      if (mounted) setState(() => _uploading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = context.watch<AppState>().currentUser;

    return Scaffold(
      backgroundColor: AppColors.bgPrimary,
      appBar: AppBar(
        backgroundColor: AppColors.bgPrimary,
        elevation: 0,
        title: Text("PERSONAL DETAILS", style: GoogleFonts.oswald(fontWeight: FontWeight.bold, letterSpacing: 1)),
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Center(
              child: Stack(
                children: [
                  Container(
                    width: 96,
                    height: 96,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border: Border.all(color: AppColors.accent, width: 2),
                      color: AppColors.bgCard,
                      image: user?.profileImageUrl != null
                          ? DecorationImage(image: NetworkImage(user!.profileImageUrl!), fit: BoxFit.cover)
                          : null,
                    ),
                    child: user?.profileImageUrl == null
                        ? Icon(Icons.person, size: 40, color: AppColors.textMuted)
                        : null,
                  ),
                  Positioned(
                    right: 0,
                    bottom: 0,
                    child: GestureDetector(
                      onTap: _uploading ? null : _pickAndUploadPhoto,
                      child: Container(
                        padding: const EdgeInsets.all(8),
                        decoration: const BoxDecoration(color: AppColors.accent, shape: BoxShape.circle),
                        child: _uploading
                            ? const SizedBox(
                                width: 14,
                                height: 14,
                                child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.bgPrimary),
                              )
                            : const Icon(Icons.camera_alt, size: 16, color: AppColors.bgPrimary),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 28),
            _detailRow("FIRST NAME", user?.firstName ?? '-'),
            _detailRow("LAST NAME", user?.lastName ?? '-'),
            _detailRow("EMAIL ADDRESS", user?.email ?? '-'),
            _detailRow("PHONE NUMBER", (user?.phone?.isNotEmpty ?? false) ? user!.phone! : 'Not provided'),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppColors.bgCard,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: AppColors.border),
              ),
              child: Row(
                children: [
                  const Icon(Icons.info_outline, color: AppColors.textMuted, size: 18),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      "Name, email and phone are set at registration and can't be edited here yet. "
                      "Contact support if these need to change.",
                      style: GoogleFonts.inter(fontSize: 11.5, color: AppColors.textMuted),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _detailRow(String label, String value) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: GoogleFonts.oswald(fontSize: 11, fontWeight: FontWeight.bold, letterSpacing: 1.0, color: AppColors.textMuted),
          ),
          const SizedBox(height: 4),
          Text(value, style: GoogleFonts.inter(fontSize: 15, color: AppColors.textPrimary)),
        ],
      ),
    );
  }
}
