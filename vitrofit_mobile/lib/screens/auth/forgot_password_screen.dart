import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../../api/api_exception.dart';
import '../../state/app_state.dart';
import '../../theme/app_theme.dart';
import '../../widgets/outline_text.dart';
import '../../widgets/slanted_button.dart';
import '../../widgets/vitro_text_field.dart';

/// Two-step forgot-password flow: request an OTP by email, then submit the
/// OTP with a new password. On success, routes back to sign-in.
class ForgotPasswordScreen extends StatefulWidget {
  const ForgotPasswordScreen({super.key});

  @override
  State<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends State<ForgotPasswordScreen> {
  final _requestFormKey = GlobalKey<FormState>();
  final _resetFormKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _otpController = TextEditingController();
  final _newPasswordController = TextEditingController();

  bool _otpSent = false;
  bool _loading = false;
  String? _error;
  String? _info;

  @override
  void dispose() {
    _emailController.dispose();
    _otpController.dispose();
    _newPasswordController.dispose();
    super.dispose();
  }

  Future<void> _requestOtp() async {
    if (!_requestFormKey.currentState!.validate()) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await context.read<AppState>().forgotPassword(_emailController.text.trim());
      setState(() {
        _otpSent = true;
        _info = 'If that email is registered, a code has been sent.';
      });
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _resetPassword() async {
    if (!_resetFormKey.currentState!.validate()) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await context.read<AppState>().resetPassword(
            email: _emailController.text.trim(),
            otp: _otpController.text.trim(),
            newPassword: _newPasswordController.text,
          );
      if (mounted) context.go('/auth');
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgPrimary,
      appBar: AppBar(backgroundColor: AppColors.bgPrimary, elevation: 0),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const OutlineText(text: "RESET ACCESS", fontSize: 22),
              Text(
                "FORGOT PASSWORD",
                style: GoogleFonts.oswald(fontSize: 26, fontWeight: FontWeight.bold, color: AppColors.accent),
              ),
              const SizedBox(height: 20),
              if (_error != null)
                Container(
                  margin: const EdgeInsets.only(bottom: 16),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppColors.errorGlow,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: AppColors.error.withOpacity(0.5)),
                  ),
                  child: Text(_error!, style: GoogleFonts.inter(color: AppColors.error, fontSize: 12.5)),
                ).animate().shake(hz: 4, duration: 350.ms),
              if (_info != null)
                Container(
                  margin: const EdgeInsets.only(bottom: 16),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppColors.successGlow,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: AppColors.success.withOpacity(0.5)),
                  ),
                  child: Text(_info!, style: GoogleFonts.inter(color: AppColors.success, fontSize: 12.5)),
                ),
              if (!_otpSent) ...[
                Text(
                  "Enter your account email and we'll send you a reset code.",
                  style: GoogleFonts.inter(fontSize: 13, color: AppColors.textSecondary),
                ),
                const SizedBox(height: 20),
                Form(
                  key: _requestFormKey,
                  child: VitroTextField(
                    label: "EMAIL ADDRESS",
                    controller: _emailController,
                    hint: "name@example.com",
                    icon: Icons.email_outlined,
                    keyboardType: TextInputType.emailAddress,
                    validator: Validators.email,
                  ),
                ),
                const SizedBox(height: 20),
                SizedBox(
                  width: double.infinity,
                  child: SlantedButton(
                    text: "SEND RESET CODE",
                    icon: Icons.send_outlined,
                    isLoading: _loading,
                    onPressed: _requestOtp,
                  ),
                ),
              ] else ...[
                Text(
                  "Enter the code we sent and choose a new password.",
                  style: GoogleFonts.inter(fontSize: 13, color: AppColors.textSecondary),
                ),
                const SizedBox(height: 20),
                Form(
                  key: _resetFormKey,
                  child: Column(
                    children: [
                      VitroTextField(
                        label: "VERIFICATION CODE",
                        controller: _otpController,
                        hint: "123456",
                        icon: Icons.pin_outlined,
                        keyboardType: TextInputType.number,
                        validator: Validators.otp,
                      ),
                      const SizedBox(height: 14),
                      VitroTextField(
                        label: "NEW PASSWORD",
                        controller: _newPasswordController,
                        hint: "••••••••",
                        icon: Icons.lock_outline,
                        obscureText: true,
                        validator: Validators.password,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),
                SizedBox(
                  width: double.infinity,
                  child: SlantedButton(
                    text: "RESET PASSWORD",
                    icon: Icons.check_circle_outline,
                    isLoading: _loading,
                    onPressed: _resetPassword,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
