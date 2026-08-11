import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/app_theme.dart';
import '../widgets/badge_chip.dart';
import '../widgets/outline_text.dart';
import '../widgets/slanted_button.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  int _activeTab = 0; // 0: Profile, 1: Login, 2: Register

  // Form Controllers
  final _loginEmailController = TextEditingController(text: "athlete@vitrofit.com");
  final _loginPasswordController = TextEditingController(text: "password123");
  
  final _regNameController = TextEditingController();
  final _regEmailController = TextEditingController();
  final _regPasswordController = TextEditingController();

  bool _obscureLoginPass = true;
  bool _obscureRegPass = true;
  bool _isLoggedIn = true;

  @override
  void dispose() {
    _loginEmailController.dispose();
    _loginPasswordController.dispose();
    _regNameController.dispose();
    _regEmailController.dispose();
    _regPasswordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      physics: const BouncingScrollPhysics(),
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Segmented Navigation Bar
          Container(
            padding: const EdgeInsets.all(4),
            decoration: BoxDecoration(
              color: AppColors.bgCard,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppColors.border),
            ),
            child: Row(
              children: [
                _buildSegmentTab(0, "MY PROFILE"),
                _buildSegmentTab(1, "SIGN IN"),
                _buildSegmentTab(2, "REGISTER"),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Tab Content
          if (_activeTab == 0) ...[
            _buildProfileTab(),
          ] else if (_activeTab == 1) ...[
            _buildLoginTab(),
          ] else ...[
            _buildRegisterTab(),
          ],
        ],
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

  // --- 1. PROFILE TAB ---
  Widget _buildProfileTab() {
    if (!_isLoggedIn) {
      return Container(
        padding: const EdgeInsets.all(32),
        alignment: Alignment.center,
        child: Column(
          children: [
            const Icon(Icons.lock_outline, size: 50, color: AppColors.accent),
            const SizedBox(height: 16),
            Text(
              "ACCESS YOUR ACCOUNT",
              style: GoogleFonts.oswald(
                fontSize: 22,
                fontWeight: FontWeight.bold,
                color: AppColors.textPrimary,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              "Please sign in or register to view your membership dashboard, booked classes, and training history.",
              style: GoogleFonts.inter(fontSize: 13, color: AppColors.textSecondary),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 20),
            SlantedButton(
              text: "SIGN IN NOW",
              onPressed: () => setState(() => _activeTab = 1),
            ),
          ],
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // User Profile Banner Card
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: AppColors.bgCard,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: AppColors.borderAccent),
            boxShadow: const [
              BoxShadow(
                color: AppColors.shadowAccent,
                blurRadius: 16,
              ),
            ],
          ),
          child: Row(
            children: [
              Container(
                width: 64,
                height: 64,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(color: AppColors.accent, width: 2),
                  image: const DecorationImage(
                    image: AssetImage('assets/images/testimonial_man.png'),
                    fit: BoxFit.cover,
                  ),
                ),
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
                          "Marcus Vance",
                          style: GoogleFonts.oswald(
                            fontSize: 22,
                            fontWeight: FontWeight.bold,
                            color: AppColors.textPrimary,
                          ),
                        ),
                        const BadgeChip(label: "PRO ATHLETE"),
                      ],
                    ),
                    const SizedBox(height: 2),
                    Text(
                      "athlete@vitrofit.com",
                      style: GoogleFonts.inter(
                        fontSize: 12,
                        color: AppColors.textMuted,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      "Member since August 2026",
                      style: GoogleFonts.inter(
                        fontSize: 11,
                        color: AppColors.accent,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 24),

        // Active Plan Card
        Text(
          "MEMBERSHIP SUBSCRIPTION",
          style: GoogleFonts.oswald(
            fontSize: 16,
            fontWeight: FontWeight.bold,
            letterSpacing: 1.0,
            color: AppColors.textMuted,
          ),
        ),
        const SizedBox(height: 10),
        Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            color: AppColors.bgSecondary,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppColors.border),
          ),
          child: Row(
            children: [
              const Icon(Icons.card_membership, size: 36, color: AppColors.accent),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      "UNLIMITED PRO MONTHLY",
                      style: GoogleFonts.oswald(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    Text(
                      "Renews on Sept 12, 2026 • \$79 / mo",
                      style: GoogleFonts.inter(
                        fontSize: 12,
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              const BadgeChip(label: "ACTIVE"),
            ],
          ),
        ),
        const SizedBox(height: 24),

        // Upcoming Reservations
        Text(
          "MY UPCOMING CLASSES",
          style: GoogleFonts.oswald(
            fontSize: 16,
            fontWeight: FontWeight.bold,
            letterSpacing: 1.0,
            color: AppColors.textMuted,
          ),
        ),
        const SizedBox(height: 10),
        _buildBookingItem("FITFUSION", "Today @ 06:00 PM", "Alexandra Rodriguez", "Studio 1"),
        _buildBookingItem("YOGA HARMONY", "Tomorrow @ 08:00 AM", "David Chen", "Zen Room"),
        const SizedBox(height: 24),

        // Quick Settings Actions
        Text(
          "ACCOUNT & PREFERENCES",
          style: GoogleFonts.oswald(
            fontSize: 16,
            fontWeight: FontWeight.bold,
            letterSpacing: 1.0,
            color: AppColors.textMuted,
          ),
        ),
        const SizedBox(height: 10),
        _buildSettingOption(Icons.person_outline, "Personal Details", () {}),
        _buildSettingOption(Icons.credit_card, "Payment & Billing", () {}),
        _buildSettingOption(Icons.notifications_none, "Notification Settings", () {}),
        _buildSettingOption(Icons.help_outline, "Customer Support", () {}),
        _buildSettingOption(Icons.logout, "Sign Out", () {
          setState(() => _isLoggedIn = false);
        }, isDanger: true),
        const SizedBox(height: 30),
      ],
    );
  }

  Widget _buildBookingItem(String title, String time, String trainer, String location) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          const Icon(Icons.event_available, color: AppColors.accent, size: 24),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: GoogleFonts.oswald(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: AppColors.textPrimary,
                  ),
                ),
                Text(
                  "$time • Coach $trainer",
                  style: GoogleFonts.inter(
                    fontSize: 12,
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
          Text(
            location,
            style: GoogleFonts.inter(
              fontSize: 11,
              color: AppColors.accent,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSettingOption(IconData icon, String label, VoidCallback onTap, {bool isDanger = false}) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.border),
      ),
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(10),
        child: ListTile(
          onTap: onTap,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          leading: Icon(icon, color: isDanger ? Colors.redAccent : AppColors.textPrimary, size: 20),
          title: Text(
            label,
            style: GoogleFonts.inter(
              fontSize: 14,
              fontWeight: FontWeight.w500,
              color: isDanger ? Colors.redAccent : AppColors.textPrimary,
            ),
          ),
          trailing: Icon(
            Icons.arrow_forward_ios,
            size: 14,
            color: isDanger ? Colors.redAccent : AppColors.textMuted,
          ),
        ),
      ),
    );
  }

  // --- 2. SIGN IN TAB ---
  Widget _buildLoginTab() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const OutlineText(text: "WELCOME BACK", fontSize: 24),
        Text(
          "SIGN IN TO VITROFIT",
          style: GoogleFonts.oswald(
            fontSize: 30,
            fontWeight: FontWeight.bold,
            color: AppColors.accent,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          "Enter your account credentials to access your fitness dashboard.",
          style: GoogleFonts.inter(fontSize: 13, color: AppColors.textSecondary),
        ),
        const SizedBox(height: 24),

        // Email Input
        Text(
          "EMAIL ADDRESS",
          style: GoogleFonts.oswald(
            fontSize: 13,
            fontWeight: FontWeight.bold,
            letterSpacing: 1.0,
            color: AppColors.textPrimary,
          ),
        ),
        const SizedBox(height: 6),
        TextField(
          controller: _loginEmailController,
          style: GoogleFonts.inter(color: AppColors.textPrimary),
          decoration: _buildInputDecoration("name@example.com", Icons.email_outlined),
        ),
        const SizedBox(height: 16),

        // Password Input
        Text(
          "PASSWORD",
          style: GoogleFonts.oswald(
            fontSize: 13,
            fontWeight: FontWeight.bold,
            letterSpacing: 1.0,
            color: AppColors.textPrimary,
          ),
        ),
        const SizedBox(height: 6),
        TextField(
          controller: _loginPasswordController,
          obscureText: _obscureLoginPass,
          style: GoogleFonts.inter(color: AppColors.textPrimary),
          decoration: _buildInputDecoration("••••••••", Icons.lock_outline).copyWith(
            suffixIcon: IconButton(
              icon: Icon(
                _obscureLoginPass ? Icons.visibility_off : Icons.visibility,
                color: AppColors.textMuted,
              ),
              onPressed: () => setState(() => _obscureLoginPass = !_obscureLoginPass),
            ),
          ),
        ),
        const SizedBox(height: 24),

        SizedBox(
          width: double.infinity,
          child: SlantedButton(
            text: "SIGN IN NOW",
            icon: Icons.login,
            onPressed: () {
              setState(() {
                _isLoggedIn = true;
                _activeTab = 0;
              });
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  backgroundColor: AppColors.accent,
                  content: Text(
                    "Welcome back to VitroFit!",
                    style: GoogleFonts.inter(color: AppColors.bgPrimary, fontWeight: FontWeight.bold),
                  ),
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  // --- 3. REGISTER TAB ---
  Widget _buildRegisterTab() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const OutlineText(text: "JOIN THE CLUB", fontSize: 24),
        Text(
          "CREATE ACCOUNT",
          style: GoogleFonts.oswald(
            fontSize: 30,
            fontWeight: FontWeight.bold,
            color: AppColors.accent,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          "Start your 7-day free trial with full access to classes & trainers.",
          style: GoogleFonts.inter(fontSize: 13, color: AppColors.textSecondary),
        ),
        const SizedBox(height: 24),

        Text("FULL NAME", style: _labelStyle()),
        const SizedBox(height: 6),
        TextField(
          controller: _regNameController,
          style: GoogleFonts.inter(color: AppColors.textPrimary),
          decoration: _buildInputDecoration("John Doe", Icons.person_outline),
        ),
        const SizedBox(height: 14),

        Text("EMAIL ADDRESS", style: _labelStyle()),
        const SizedBox(height: 6),
        TextField(
          controller: _regEmailController,
          style: GoogleFonts.inter(color: AppColors.textPrimary),
          decoration: _buildInputDecoration("john@example.com", Icons.email_outlined),
        ),
        const SizedBox(height: 14),

        Text("PASSWORD", style: _labelStyle()),
        const SizedBox(height: 6),
        TextField(
          controller: _regPasswordController,
          obscureText: _obscureRegPass,
          style: GoogleFonts.inter(color: AppColors.textPrimary),
          decoration: _buildInputDecoration("••••••••", Icons.lock_outline).copyWith(
            suffixIcon: IconButton(
              icon: Icon(
                _obscureRegPass ? Icons.visibility_off : Icons.visibility,
                color: AppColors.textMuted,
              ),
              onPressed: () => setState(() => _obscureRegPass = !_obscureRegPass),
            ),
          ),
        ),
        const SizedBox(height: 24),

        SizedBox(
          width: double.infinity,
          child: SlantedButton(
            text: "CREATE ACCOUNT",
            icon: Icons.arrow_forward,
            onPressed: () {
              setState(() {
                _isLoggedIn = true;
                _activeTab = 0;
              });
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  backgroundColor: AppColors.accent,
                  content: Text(
                    "Account created! Welcome to VitroFit.",
                    style: GoogleFonts.inter(color: AppColors.bgPrimary, fontWeight: FontWeight.bold),
                  ),
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  TextStyle _labelStyle() {
    return GoogleFonts.oswald(
      fontSize: 13,
      fontWeight: FontWeight.bold,
      letterSpacing: 1.0,
      color: AppColors.textPrimary,
    );
  }

  InputDecoration _buildInputDecoration(String hint, IconData icon) {
    return InputDecoration(
      hintText: hint,
      hintStyle: GoogleFonts.inter(color: AppColors.textMuted),
      prefixIcon: Icon(icon, color: AppColors.accent, size: 20),
      filled: true,
      fillColor: AppColors.bgCard,
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: AppColors.border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: AppColors.accent, width: 1.5),
      ),
    );
  }
}
