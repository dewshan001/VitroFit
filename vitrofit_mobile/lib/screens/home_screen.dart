import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../state/app_state.dart';
import '../theme/app_theme.dart';
import '../widgets/animated_glow_background.dart';
import '../widgets/outline_text.dart';
import '../widgets/skeleton_box.dart';
import '../widgets/slanted_button.dart';
import '../widgets/workout_card.dart';
import 'workout_detail_sheet.dart';

class HomeScreen extends StatefulWidget {
  final Function(int) onNavigateToTab;

  const HomeScreen({
    super.key,
    required this.onNavigateToTab,
  });

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _scrollController = ScrollController();

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final appState = context.watch<AppState>();
    return Stack(
      children: [
        Positioned.fill(child: AmbientGlowBackground(scrollController: _scrollController)),
        RefreshIndicator(
          color: AppColors.accent,
          backgroundColor: AppColors.bgCard,
          onRefresh: () => appState.loadWorkouts(),
          child: SingleChildScrollView(
            controller: _scrollController,
            physics: const AlwaysScrollableScrollPhysics(parent: BouncingScrollPhysics()),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // 1. HERO BANNER
                _buildHeroSection(context),

                const SizedBox(height: 24),

                // 2. STATS BAR
                _buildStatsBar(),

                const SizedBox(height: 36),

                // 3. FEATURED WORKOUTS CAROUSEL
                _buildFeaturedWorkouts(context, appState),

                const SizedBox(height: 36),

                // 4. WHY US FEATURES
                _buildWhyUsSection(),

                const SizedBox(height: 36),

                // 5. BOTTOM CTA BANNER
                _buildCtaBanner(context),

                const SizedBox(height: 40),
              ],
            ),
          ),
        ),
      ],
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
              const OutlineText(text: "ACHIEVE MORE", fontSize: 32)
                  .animate()
                  .fadeIn(duration: 450.ms)
                  .slideX(begin: -0.1, end: 0, curve: Curves.easeOutCubic),
              Text(
                "THAN JUST FITNESS",
                style: GoogleFonts.oswald(
                  fontSize: 32,
                  fontWeight: FontWeight.w900,
                  height: 1.1,
                  letterSpacing: 1.5,
                  color: AppColors.textPrimary,
                ),
              )
                  .animate(delay: 80.ms)
                  .fadeIn(duration: 450.ms)
                  .slideX(begin: -0.1, end: 0, curve: Curves.easeOutCubic),
              const SizedBox(height: 12),
              Text(
                "Combine strength, flexibility, and endurance in a supportive community designed for constant growth.",
                style: GoogleFonts.inter(
                  fontSize: 14,
                  height: 1.5,
                  color: AppColors.textSecondary,
                ),
              ).animate(delay: 180.ms).fadeIn(duration: 450.ms),
              const SizedBox(height: 24),
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: [
                  SlantedButton(
                    text: "START NOW",
                    icon: Icons.arrow_forward,
                    onPressed: () => widget.onNavigateToTab(1), // Go to Workouts tab
                  ),
                  SlantedButton(
                    text: "FREE TRIAL",
                    isSecondary: true,
                    onPressed: () => widget.onNavigateToTab(2), // Go to Timetable tab
                  ),
                ],
              ).animate(delay: 280.ms).fadeIn(duration: 450.ms).slideY(begin: 0.15, end: 0, curve: Curves.easeOutCubic),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildStatsBar() {
    final stats = [
      {'val': 500.0, 'suffix': '+', 'label': 'Members'},
      {'val': 30.0, 'suffix': '+', 'label': 'Classes/Wk'},
      {'val': 10.0, 'suffix': '', 'label': 'Trainers'},
      {'val': 99.0, 'suffix': '%', 'label': 'Satisfaction'},
    ];

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20),
      padding: const EdgeInsets.symmetric(vertical: 18, horizontal: 12),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(16),
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
        children: List.generate(stats.length, (i) {
          final s = stats[i];
          return Expanded(
            child: Row(
              children: [
                if (i > 0)
                  Container(
                    width: 1,
                    height: 28,
                    color: AppColors.border,
                  ),
                Expanded(
                  child: Column(
                    children: [
                      TweenAnimationBuilder<double>(
                        tween: Tween(begin: 0, end: s['val'] as double),
                        duration: Duration(milliseconds: 900 + i * 150),
                        curve: Curves.easeOutCubic,
                        builder: (context, value, child) {
                          final isDecimalFree = value == value.roundToDouble();
                          return FittedBox(
                            fit: BoxFit.scaleDown,
                            child: Text(
                              '${isDecimalFree ? value.round() : value.toStringAsFixed(0)}${s['suffix']}',
                              style: GoogleFonts.oswald(
                                fontSize: 22,
                                fontWeight: FontWeight.bold,
                                color: AppColors.accent,
                              ),
                            ),
                          );
                        },
                      ),
                      const SizedBox(height: 2),
                      FittedBox(
                        fit: BoxFit.scaleDown,
                        child: Text(
                          s['label'] as String,
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
                ),
              ],
            ),
          );
        }),
      ),
    )
        .animate()
        .fadeIn(duration: 500.ms, delay: 150.ms)
        .slideY(begin: 0.2, end: 0, curve: Curves.easeOutCubic);
  }

  Widget _buildFeaturedWorkouts(BuildContext context, AppState appState) {
    final featured = appState.workouts.take(4).toList();

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
                      "FEATURED WORKOUTS",
                      style: GoogleFonts.oswald(
                        fontSize: 22,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 1.0,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    Text(
                      "From the studio's live workout catalog",
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
                onTap: () => widget.onNavigateToTab(1),
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
        if (appState.workoutsLoading && featured.isEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Row(
              children: List.generate(
                2,
                (i) => const Expanded(
                  child: Padding(
                    padding: EdgeInsets.only(right: 12),
                    child: SkeletonBox(height: 190, borderRadius: 12),
                  ),
                ),
              ),
            ),
          )
        else if (featured.isEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Text(
              "No workouts available yet.",
              style: GoogleFonts.inter(color: AppColors.textSecondary),
            ),
          )
        else
          SizedBox(
            height: 230,
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              scrollDirection: Axis.horizontal,
              itemCount: featured.length,
              itemBuilder: (context, index) {
                final item = featured[index];
                return Container(
                  width: 240,
                  margin: const EdgeInsets.only(right: 16),
                  child: WorkoutCard(
                    workout: item,
                    onTap: () => WorkoutDetailSheet.show(context, item),
                  ),
                ).animate(delay: (index * 80).ms).fadeIn(duration: 350.ms).slideX(begin: 0.15, end: 0, curve: Curves.easeOut);
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
              return _WhyUsCard(
                icon: f['icon'] as IconData,
                title: f['title'] as String,
                desc: f['desc'] as String,
              )
                  .animate(delay: (index * 90).ms)
                  .fadeIn(duration: 400.ms)
                  .slideY(begin: 0.15, end: 0, curve: Curves.easeOutCubic);
            },
          ),
        ],
      ),
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
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              SlantedButton(
                text: "JOIN NOW FREE",
                icon: Icons.flash_on,
                onPressed: () => widget.onNavigateToTab(3), // Go to Profile tab
              ),
              SlantedButton(
                text: "ABOUT US",
                isSecondary: true,
                onPressed: () => context.push('/main/about'),
              ),
            ],
          ),
        ],
      ),
    )
        .animate()
        .fadeIn(duration: 500.ms)
        .slideY(begin: 0.1, end: 0, curve: Curves.easeOutCubic);
  }
}

class _WhyUsCard extends StatefulWidget {
  final IconData icon;
  final String title;
  final String desc;

  const _WhyUsCard({required this.icon, required this.title, required this.desc});

  @override
  State<_WhyUsCard> createState() => _WhyUsCardState();
}

class _WhyUsCardState extends State<_WhyUsCard> {
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTapDown: (_) => setState(() => _pressed = true),
      onTapUp: (_) => setState(() => _pressed = false),
      onTapCancel: () => setState(() => _pressed = false),
      child: AnimatedScale(
        scale: _pressed ? 0.96 : 1.0,
        duration: const Duration(milliseconds: 120),
        curve: Curves.easeOut,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: AppColors.bgCard,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: _pressed ? AppColors.borderAccent : AppColors.border),
            boxShadow: _pressed
                ? const [BoxShadow(color: AppColors.shadowAccent, blurRadius: 14, spreadRadius: 1)]
                : [],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [AppColors.accent.withOpacity(0.22), AppColors.accent.withOpacity(0.06)],
                  ),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(widget.icon, color: AppColors.accent, size: 22),
              ),
              const SizedBox(height: 12),
              Text(
                widget.title,
                style: GoogleFonts.oswald(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                widget.desc,
                style: GoogleFonts.inter(
                  fontSize: 11,
                  color: AppColors.textSecondary,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
