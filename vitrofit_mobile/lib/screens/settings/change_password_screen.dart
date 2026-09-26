import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../../api/api_exception.dart';
import '../../state/app_state.dart';
import '../../theme/app_theme.dart';
import '../../widgets/slanted_button.dart';
import '../../widgets/vitro_text_field.dart';

class ChangePasswordScreen extends StatefulWidget {
  const ChangePasswordScreen({super.key});

  @override
  State<ChangePasswordScreen> createState() => _ChangePasswordScreenState();
}

class _ChangePasswordScreenState extends State<ChangePasswordScreen> {
  final _formKey = GlobalKey<FormState>();
  final _currentController = TextEditingController();
  final _newController = TextEditingController();
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _currentController.dispose();
    _newController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await context.read<AppState>().changePassword(
            currentPassword: _currentController.text,
            newPassword: _newController.text,
          );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            backgroundColor: AppColors.success,
            content: Text("Password updated successfully.", style: GoogleFonts.inter(fontWeight: FontWeight.bold)),
          ),
        );
        context.pop();
      }
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
      appBar: AppBar(
        backgroundColor: AppColors.bgPrimary,
        elevation: 0,
        title: Text("CHANGE PASSWORD", style: GoogleFonts.oswald(fontWeight: FontWeight.bold, letterSpacing: 1)),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
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
                VitroTextField(
                  label: "CURRENT PASSWORD",
                  controller: _currentController,
                  hint: "••••••••",
                  icon: Icons.lock_outline,
                  obscureText: true,
                  validator: (v) => Validators.required(v, label: 'Current password'),
                ),
                const SizedBox(height: 16),
                VitroTextField(
                  label: "NEW PASSWORD",
                  controller: _newController,
                  hint: "••••••••",
                  icon: Icons.lock_reset,
                  obscureText: true,
                  validator: Validators.password,
                ),
                const SizedBox(height: 24),
                SizedBox(
                  width: double.infinity,
                  child: SlantedButton(
                    text: "UPDATE PASSWORD",
                    icon: Icons.check,
                    isLoading: _loading,
                    onPressed: _submit,
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
