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

class VerifyEmailScreen extends StatefulWidget {
  final String email;
  const VerifyEmailScreen({super.key, required this.email});

  @override
  State<VerifyEmailScreen> createState() => _VerifyEmailScreenState();
}

class _VerifyEmailScreenState extends State<VerifyEmailScreen> {
  final _formKey = GlobalKey<FormState>();
  final _otpController = TextEditingController();
  bool _loading = false;
  bool _resending = false;
  String? _error;
  String? _info;
  String? _pending; // gym owner: verified, awaiting admin approval

  @override
  void dispose() {
    _otpController.dispose();
    super.dispose();
  }

  Future<void> _verify() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _loading = true;
      _error = null;
      _info = null;
    });
    try {
      final pending = await context.read<AppState>().verifyEmail(
        email: widget.email,
        otp: _otpController.text.trim(),
      );
      if (pending != null && mounted) setState(() => _pending = pending);
      // Otherwise the router redirect handles navigation to /main once
      // authStatus flips.
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } catch (_) {
      setState(() => _error = 'Something went wrong. Please try again.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _resend() async {
    setState(() {
      _resending = true;
      _error = null;
      _info = null;
    });
    try {
      await context.read<AppState>().resendVerification(widget.email);
      setState(() => _info = 'A new code has been sent to ${widget.email}.');
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } catch (_) {
      setState(() => _error = 'Could not resend the code. Please try again.');
    } finally {
      if (mounted) setState(() => _resending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_pending != null) {
      return Scaffold(
        backgroundColor: AppColors.bgPrimary,
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(
                  Icons.hourglass_top,
                  color: AppColors.accent,
                  size: 44,
                ),
                const SizedBox(height: 16),
                Text(
                  "APPLICATION RECEIVED",
                  style: GoogleFonts.oswald(
                    fontSize: 28,
                    fontWeight: FontWeight.bold,
                    color: AppColors.accent,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  _pending!,
                  style: GoogleFonts.inter(
                    fontSize: 14,
                    color: AppColors.textSecondary,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  "You'll get an email once VitroFit has reviewed your gym. "
                  "You can sign in after it's approved.",
                  style: GoogleFonts.inter(
                    fontSize: 13,
                    color: AppColors.textMuted,
                  ),
                ),
                const SizedBox(height: 28),
                SizedBox(
                  width: double.infinity,
                  child: SlantedButton(
                    text: "BACK TO SIGN IN",
                    icon: Icons.login,
                    onPressed: () => context.go('/auth'),
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    }
    return Scaffold(
      backgroundColor: AppColors.bgPrimary,
      appBar: AppBar(backgroundColor: AppColors.bgPrimary, elevation: 0),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const OutlineText(text: "ALMOST THERE", fontSize: 24),
                Text(
                  "VERIFY YOUR EMAIL",
                  style: GoogleFonts.oswald(
                    fontSize: 28,
                    fontWeight: FontWeight.bold,
                    color: AppColors.accent,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  "We sent a 6-digit code to ${widget.email}. Enter it below to activate your account.",
                  style: GoogleFonts.inter(
                    fontSize: 13,
                    color: AppColors.textSecondary,
                  ),
                ),
                const SizedBox(height: 24),
                if (_error != null)
                  Container(
                    margin: const EdgeInsets.only(bottom: 16),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppColors.errorGlow,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(
                        color: AppColors.error.withValues(alpha: 0.5),
                      ),
                    ),
                    child: Text(
                      _error!,
                      style: GoogleFonts.inter(
                        color: AppColors.error,
                        fontSize: 12.5,
                      ),
                    ),
                  ).animate().shake(hz: 4, duration: 350.ms),
                if (_info != null)
                  Container(
                    margin: const EdgeInsets.only(bottom: 16),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppColors.successGlow,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(
                        color: AppColors.success.withValues(alpha: 0.5),
                      ),
                    ),
                    child: Text(
                      _info!,
                      style: GoogleFonts.inter(
                        color: AppColors.success,
                        fontSize: 12.5,
                      ),
                    ),
                  ).animate().fadeIn(duration: 200.ms),
                VitroTextField(
                  label: "VERIFICATION CODE",
                  controller: _otpController,
                  hint: "123456",
                  icon: Icons.pin_outlined,
                  keyboardType: TextInputType.number,
                  validator: Validators.otp,
                ),
                const SizedBox(height: 24),
                SizedBox(
                  width: double.infinity,
                  child: SlantedButton(
                    text: "VERIFY & CONTINUE",
                    icon: Icons.check_circle_outline,
                    isLoading: _loading,
                    onPressed: _verify,
                  ),
                ),
                const SizedBox(height: 12),
                Center(
                  child: TextButton(
                    onPressed: _resending ? null : _resend,
                    child: Text(
                      _resending ? "SENDING..." : "RESEND CODE",
                      style: GoogleFonts.oswald(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: AppColors.textMuted,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
