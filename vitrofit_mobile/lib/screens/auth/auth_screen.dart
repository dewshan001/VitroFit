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

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  int _activeTab = 0; // 0: Sign In, 1: Register

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgPrimary,
      body: SafeArea(
        child: SingleChildScrollView(
          physics: const BouncingScrollPhysics(),
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: 10,
                    height: 24,
                    decoration: BoxDecoration(
                      color: AppColors.accent,
                      borderRadius: BorderRadius.circular(2),
                      boxShadow: const [BoxShadow(color: AppColors.shadowAccent, blurRadius: 10)],
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    "VITROFIT",
                    style: GoogleFonts.oswald(
                      fontSize: 22,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 2.5,
                      color: AppColors.textPrimary,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 28),
              Container(
                padding: const EdgeInsets.all(4),
                decoration: BoxDecoration(
                  color: AppColors.bgCard,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppColors.border),
                ),
                child: Row(
                  children: [
                    _buildSegmentTab(0, "SIGN IN"),
                    _buildSegmentTab(1, "REGISTER"),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              AnimatedSwitcher(
                duration: const Duration(milliseconds: 250),
                child: _activeTab == 0
                    ? const _SignInForm(key: ValueKey('signin'))
                    : const _RegisterForm(key: ValueKey('register')),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSegmentTab(int index, String label) {
    final isSelected = _activeTab == index;
    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() => _activeTab = index),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          padding: const EdgeInsets.symmetric(vertical: 10),
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: isSelected ? AppColors.accent : Colors.transparent,
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(
            label,
            style: GoogleFonts.oswald(
              fontSize: 13,
              fontWeight: FontWeight.bold,
              letterSpacing: 1.0,
              color: isSelected ? AppColors.bgPrimary : AppColors.textSecondary,
            ),
          ),
        ),
      ),
    );
  }
}

class _ErrorBanner extends StatelessWidget {
  final String message;
  const _ErrorBanner({required this.message});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.errorGlow,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.error.withOpacity(0.5)),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline, color: AppColors.error, size: 18),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              message,
              style: GoogleFonts.inter(color: AppColors.error, fontSize: 12.5, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    ).animate().fadeIn(duration: 200.ms).shake(hz: 4, duration: 350.ms);
  }
}

class _SignInForm extends StatefulWidget {
  const _SignInForm({super.key});

  @override
  State<_SignInForm> createState() => _SignInFormState();
}

class _SignInFormState extends State<_SignInForm> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _obscure = true;
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await context.read<AppState>().login(
            email: _emailController.text.trim(),
            password: _passwordController.text,
          );
      // Router redirect handles navigation to /main once authStatus flips.
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } catch (_) {
      setState(() => _error = 'Something went wrong. Please try again.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const OutlineText(text: "WELCOME BACK", fontSize: 24),
          Text(
            "SIGN IN TO VITROFIT",
            style: GoogleFonts.oswald(fontSize: 28, fontWeight: FontWeight.bold, color: AppColors.accent),
          ),
          const SizedBox(height: 6),
          Text(
            "Enter your account credentials to access your fitness dashboard.",
            style: GoogleFonts.inter(fontSize: 13, color: AppColors.textSecondary),
          ),
          const SizedBox(height: 20),
          if (_error != null) _ErrorBanner(message: _error!),
          VitroTextField(
            label: "EMAIL ADDRESS",
            controller: _emailController,
            hint: "name@example.com",
            icon: Icons.email_outlined,
            keyboardType: TextInputType.emailAddress,
            validator: Validators.email,
          ),
          const SizedBox(height: 16),
          VitroTextField(
            label: "PASSWORD",
            controller: _passwordController,
            hint: "••••••••",
            icon: Icons.lock_outline,
            obscureText: _obscure,
            validator: (v) => Validators.required(v, label: 'Password'),
            suffixIcon: IconButton(
              icon: Icon(_obscure ? Icons.visibility_off : Icons.visibility, color: AppColors.textMuted),
              onPressed: () => setState(() => _obscure = !_obscure),
            ),
          ),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(
              onPressed: () => context.push('/forgot-password'),
              child: Text(
                "FORGOT PASSWORD?",
                style: GoogleFonts.oswald(fontSize: 12, color: AppColors.textMuted, fontWeight: FontWeight.bold),
              ),
            ),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: SlantedButton(
              text: "SIGN IN NOW",
              icon: Icons.login,
              isLoading: _loading,
              onPressed: _submit,
            ),
          ),
        ],
      ),
    );
  }
}

class _RegisterForm extends StatefulWidget {
  const _RegisterForm({super.key});

  @override
  State<_RegisterForm> createState() => _RegisterFormState();
}

class _RegisterFormState extends State<_RegisterForm> {
  final _formKey = GlobalKey<FormState>();
  final _firstNameController = TextEditingController();
  final _lastNameController = TextEditingController();
  final _emailController = TextEditingController();
  final _phoneController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _obscure = true;
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _firstNameController.dispose();
    _lastNameController.dispose();
    _emailController.dispose();
    _phoneController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    final email = _emailController.text.trim();
    try {
      await context.read<AppState>().register(
            firstName: _firstNameController.text.trim(),
            lastName: _lastNameController.text.trim(),
            email: email,
            phone: _phoneController.text.trim(),
            password: _passwordController.text,
          );
      if (mounted) context.push('/verify-email', extra: email);
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } catch (_) {
      setState(() => _error = 'Something went wrong. Please try again.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const OutlineText(text: "JOIN THE CLUB", fontSize: 24),
          Text(
            "CREATE ACCOUNT",
            style: GoogleFonts.oswald(fontSize: 28, fontWeight: FontWeight.bold, color: AppColors.accent),
          ),
          const SizedBox(height: 6),
          Text(
            "Register with VitroFit to build your personal training timetable.",
            style: GoogleFonts.inter(fontSize: 13, color: AppColors.textSecondary),
          ),
          const SizedBox(height: 20),
          if (_error != null) _ErrorBanner(message: _error!),
          Row(
            children: [
              Expanded(
                child: VitroTextField(
                  label: "FIRST NAME",
                  controller: _firstNameController,
                  hint: "John",
                  icon: Icons.person_outline,
                  validator: (v) => Validators.required(v, label: 'First name'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: VitroTextField(
                  label: "LAST NAME",
                  controller: _lastNameController,
                  hint: "Doe",
                  icon: Icons.person_outline,
                  validator: (v) => Validators.required(v, label: 'Last name'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          VitroTextField(
            label: "EMAIL ADDRESS",
            controller: _emailController,
            hint: "john@example.com",
            icon: Icons.email_outlined,
            keyboardType: TextInputType.emailAddress,
            validator: Validators.email,
          ),
          const SizedBox(height: 14),
          VitroTextField(
            label: "PHONE NUMBER",
            controller: _phoneController,
            hint: "+94 71 234 5678",
            icon: Icons.phone_outlined,
            keyboardType: TextInputType.phone,
            validator: (v) => Validators.required(v, label: 'Phone number'),
          ),
          const SizedBox(height: 14),
          VitroTextField(
            label: "PASSWORD",
            controller: _passwordController,
            hint: "••••••••",
            icon: Icons.lock_outline,
            obscureText: _obscure,
            validator: Validators.password,
            suffixIcon: IconButton(
              icon: Icon(_obscure ? Icons.visibility_off : Icons.visibility, color: AppColors.textMuted),
              onPressed: () => setState(() => _obscure = !_obscure),
            ),
          ),
          const SizedBox(height: 24),
          SizedBox(
            width: double.infinity,
            child: SlantedButton(
              text: "CREATE ACCOUNT",
              icon: Icons.arrow_forward,
              isLoading: _loading,
              onPressed: _submit,
            ),
          ),
        ],
      ),
    );
  }
}
