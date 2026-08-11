import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../models/fitness_data.dart';
import '../theme/app_theme.dart';
import '../widgets/badge_chip.dart';
import '../widgets/class_card.dart';
import '../widgets/outline_text.dart';
import '../widgets/slanted_button.dart';
import '../widgets/trainer_card.dart';
import 'class_detail_sheet.dart';

class HomeScreen extends StatelessWidget {
  final Function(int) onNavigateToTab;

  const HomeScreen({
    super.key,
    required this.onNavigateToTab,
  });

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      physics: const BouncingScrollPhysics(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 1. HERO BANNER
          _buildHeroSection(context),

          const SizedBox(height: 24),

          // 2. STATS BAR
          _buildStatsBar(),

          const SizedBox(height: 32),

          // 3. DAILY FITNESS TRACKER WIDGET
          _buildDailyActivityTracker(context),

          const SizedBox(height: 36),

          // 4. FEATURED CLASSES CAROUSEL
          _buildFeaturedClasses(context),

          const SizedBox(height: 36),

          // 5. WHY US FEATURES
          _buildWhyUsSection(),

          const SizedBox(height: 36),

          // 6. CERTIFIED TRAINERS
          _buildTrainersSection(),

          const SizedBox(height: 36),

          // 7. BOTTOM CTA BANNER
          _buildCtaBanner(context),

          const SizedBox(height: 40),
        ],
      ),
    );
  }

  Widget _buildHeroSection(BuildContext context) {
    return Stack(
      children: [
        // Hero Background Image
        AspectRatio(
          aspectRatio: 4 / 3,
          child: Image.asset(
            'assets/images/hero_athlete.png',
            fit: BoxFit.cover,
            errorBuilder: (context, error, stackTrace) => Container(color: AppColors.bgSecondary),
          ),
        ),
        // Dark Overlay Gradients
        Positioned.fill(
          child: Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  AppColors.bgPrimary.withOpacity(0.3),
                  AppColors.bgPrimary.withOpacity(0.85),
                  AppColors.bgPrimary,
                ],
                stops: const [0.0, 0.6, 1.0],
              ),
            ),
          ),
        ),
        // Content
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 20),
              Row(
                children: [
                  Container(
                    width: 24,
                    height: 3,
                    color: AppColors.accent,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    "ELITE FITNESS STUDIO",
                    style: GoogleFonts.oswald(
                      fontSize: 13,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 3.0,
                      color: AppColors.accent,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              const OutlineText(text: "ACHIEVE MORE", fontSize: 32),
              Text(
                "THAN JUST FITNESS",
                style: GoogleFonts.oswald(
                  fontSize: 32,
                  fontWeight: FontWeight.w900,
                  height: 1.1,
                  letterSpacing: 1.5,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 12),
              Text(
                "Combine strength, flexibility, and endurance in a supportive community designed for constant growth.",
                style: GoogleFonts.inter(
                  fontSize: 14,
                  height: 1.5,
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: 24),
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: [
                  SlantedButton(
                    text: "START NOW",
                    icon: Icons.arrow_forward,
                    onPressed: () => onNavigateToTab(1), // Go to Classes tab
                  ),
                  SlantedButton(
                    text: "FREE TRIAL",
                    isSecondary: true,
                    onPressed: () => onNavigateToTab(2), // Go to Timetable tab
                  ),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildStatsBar() {
    final stats = [
      {'val': '500+', 'label': 'Members'},
      {'val': '30+', 'label': 'Classes/Wk'},
      {'val': '10', 'label': 'Trainers'},
      {'val': '99%', 'label': 'Satisfaction'},
    ];

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20),
      padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 12),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.borderAccent),
        boxShadow: const [
          BoxShadow(
            color: AppColors.shadowAccent,
            blurRadius: 15,
            spreadRadius: 1,
          )
        ],
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: stats.map((s) {
          return Expanded(
            child: Column(
              children: [
                FittedBox(
                  fit: BoxFit.scaleDown,
                  child: Text(
                    s['val']!,
                    style: GoogleFonts.oswald(
                      fontSize: 22,
                      fontWeight: FontWeight.bold,
                      color: AppColors.accent,
                    ),
                  ),
                ),
                const SizedBox(height: 2),
                FittedBox(
                  fit: BoxFit.scaleDown,
                  child: Text(
                    s['label']!,
                    style: GoogleFonts.inter(
                      fontSize: 11,
                      fontWeight: FontWeight.w500,
                      color: AppColors.textSecondary,
                    ),
                    maxLines: 1,
                  ),
                ),
              ],
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildDailyActivityTracker(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.bgSecondary,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      "TODAY'S ACTIVITY",
                      style: GoogleFonts.oswald(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 1.0,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    Text(
                      "Daily goal: 600 kcal burn",
                      style: GoogleFonts.inter(
                        fontSize: 12,
                        color: AppColors.textMuted,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              const BadgeChip(label: "75% DONE"),
            ],
          ),
          const SizedBox(height: 16),
          // Linear Progress Bar
          ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: LinearProgressIndicator(
              value: 0.75,
              minHeight: 10,
              backgroundColor: AppColors.bgCardHover,
              valueColor: const AlwaysStoppedAnimation<Color>(AppColors.accent),
            ),
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _buildTrackerStat(Icons.local_fire_department, "450 / 600", "CALORIES BURNED"),
              _buildTrackerStat(Icons.timer, "45 MINS", "WORKOUT TIME"),
              _buildTrackerStat(Icons.favorite, "132 BPM", "AVG HEART RATE"),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildTrackerStat(IconData icon, String val, String label) {
    return Expanded(
      child: Column(
        children: [
          Icon(icon, size: 18, color: AppColors.accent),
          const SizedBox(height: 4),
          Text(
            val,
            style: GoogleFonts.oswald(
              fontSize: 15,
              fontWeight: FontWeight.bold,
              color: AppColors.textPrimary,
            ),
            textAlign: TextAlign.center,
          ),
          Text(
            label,
            style: GoogleFonts.inter(
              fontSize: 9,
              color: AppColors.textMuted,
              fontWeight: FontWeight.bold,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildFeaturedClasses(BuildContext context) {
    final featured = SampleData.classes.take(4).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20.0),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      "FEATURED CLASSES",
                      style: GoogleFonts.oswald(
                        fontSize: 22,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 1.0,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    Text(
                      "High impact workout programs",
                      style: GoogleFonts.inter(
                        fontSize: 12,
                        color: AppColors.textMuted,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              GestureDetector(
                onTap: () => onNavigateToTab(1),
                child: Text(
                  "SEE ALL →",
                  style: GoogleFonts.oswald(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                    color: AppColors.accent,
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        SizedBox(
          height: 350,
          child: ListView.builder(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            scrollDirection: Axis.horizontal,
            itemCount: featured.length,
            itemBuilder: (context, index) {
              final item = featured[index];
              return Container(
                width: 280,
                margin: const EdgeInsets.only(right: 16),
                child: ClassCard(
                  classItem: item,
                  onTap: () => ClassDetailSheet.show(context, item),
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  Widget _buildWhyUsSection() {
    final features = [
      {'icon': Icons.fitness_center, 'title': 'Modern Equipment', 'desc': 'State of the art resistance & cardio machinery.'},
      {'icon': Icons.military_tech, 'title': 'Elite Trainers', 'desc': 'Certified coaches dedicated to your success.'},
      {'icon': Icons.bolt, 'title': 'Customized Programs', 'desc': 'Tailored workouts for your specific goals.'},
      {'icon': Icons.groups, 'title': 'Dynamic Community', 'desc': 'Supportive atmosphere that motivates daily.'},
    ];

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const OutlineText(text: "WHY CHOOSE", fontSize: 24),
          Text(
            "THE VITROFIT ADVANTAGE",
            style: GoogleFonts.oswald(
              fontSize: 24,
              fontWeight: FontWeight.bold,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 16),
          GridView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 2,
              crossAxisSpacing: 12,
              mainAxisSpacing: 12,
              childAspectRatio: 0.78,
            ),
            itemCount: features.length,
            itemBuilder: (context, index) {
              final f = features[index];
              return Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: AppColors.bgCard,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppColors.border),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(f['icon'] as IconData, color: AppColors.accent, size: 28),
                    const SizedBox(height: 10),
                    Text(
                      f['title'] as String,
                      style: GoogleFonts.oswald(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      f['desc'] as String,
                      style: GoogleFonts.inter(
                        fontSize: 11,
                        color: AppColors.textSecondary,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _buildTrainersSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                "EXPERT COACHES",
                style: GoogleFonts.oswald(
                  fontSize: 22,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 1.0,
                  color: AppColors.textPrimary,
                ),
              ),
              Text(
                "Guided by industry professionals",
                style: GoogleFonts.inter(
                  fontSize: 12,
                  color: AppColors.textMuted,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        SizedBox(
          height: 350,
          child: ListView.builder(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            scrollDirection: Axis.horizontal,
            itemCount: SampleData.trainers.length,
            itemBuilder: (context, index) {
              return TrainerCard(trainer: SampleData.trainers[index]);
            },
          ),
        ),

      ],
    );
  }

  Widget _buildCtaBanner(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20),
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: AppColors.bgSecondary,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.borderAccent),
        image: const DecorationImage(
          image: AssetImage('assets/images/strength_training.png'),
          fit: BoxFit.cover,
          opacity: 0.15,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const OutlineText(text: "READY TO ELEVATE", fontSize: 22),
          Text(
            "YOUR FITNESS JOURNEY?",
            style: GoogleFonts.oswald(
              fontSize: 24,
              fontWeight: FontWeight.w900,
              color: AppColors.accent,
            ),
          ),
          const SizedBox(height: 10),
          Text(
            "Join VitroFit mobile today and gain unlimited access to elite coaching and personalized workouts.",
            style: GoogleFonts.inter(
              fontSize: 13,
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 20),
          SlantedButton(
            text: "JOIN NOW FREE",
            icon: Icons.flash_on,
            onPressed: () => onNavigateToTab(4), // Go to Auth/Profile
          ),
        ],
      ),
    );
  }
}
