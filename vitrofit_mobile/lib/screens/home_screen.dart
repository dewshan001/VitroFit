import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../models/timetable_slot.dart';
import '../models/user_profile.dart';
import '../models/workout.dart';
import '../state/app_state.dart';
import '../theme/app_theme.dart';
import '../widgets/animated_glow_background.dart';
import '../widgets/liquid_glass.dart';
import '../widgets/outline_text.dart';
import '../widgets/skeleton_box.dart';
import '../widgets/slanted_button.dart';
import '../widgets/workout_card.dart';
import 'workout_detail_sheet.dart';

class HomeScreen extends StatefulWidget {
  final Function(int) onNavigateToTab;

  const HomeScreen({super.key, required this.onNavigateToTab});

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
        Positioned.fill(
          child: AmbientGlowBackground(scrollController: _scrollController),
        ),
        RefreshIndicator(
          color: AppColors.accent,
          backgroundColor: AppColors.bgCard,
          onRefresh: () => appState.loadWorkouts(),
          child: SingleChildScrollView(
            controller: _scrollController,
            physics: const AlwaysScrollableScrollPhysics(
              parent: BouncingScrollPhysics(),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // 1. HERO BANNER
                _buildHeroSection(context, appState),

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

                const SizedBox(height: 110),
              ],
            ),
          ),
        ),
      ],
    );
  }

  String _greeting() {
    final hour = DateTime.now().hour;
    if (hour < 12) return "GOOD MORNING";
    if (hour < 17) return "GOOD AFTERNOON";
    return "GOOD EVENING";
  }

  TimetableSlot? _nextUpSlot(AppState appState) {
    return appState.timetableSlots.isNotEmpty
        ? appState.timetableSlots.first
        : null;
  }

  Widget _buildHeroSection(BuildContext context, AppState appState) {
    final user = appState.currentUser;
    final nextUp = _nextUpSlot(appState);

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(20),
        child: Stack(
          children: [
            // Background texture image
            Positioned.fill(
              child: Image.asset(
                'assets/images/hero_athlete.png',
                fit: BoxFit.cover,
                errorBuilder: (context, error, stackTrace) =>
                    Container(color: AppColors.bgSecondary),
              ),
            ),
            // Dark overlay + border so it reads as a dashboard card
            Positioned.fill(
              child: Container(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      AppColors.bgPrimary.withOpacity(0.92),
                      AppColors.bgPrimary.withOpacity(0.75),
                      AppColors.bgSecondary.withOpacity(0.55),
                    ],
                  ),
                  border: Border.all(color: AppColors.borderAccent),
                  borderRadius: BorderRadius.circular(20),
                ),
              ),
            ),
            // Content (drives the Stack's/card's size)
            Padding(
              padding: const EdgeInsets.all(18),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                                  _greeting(),
                                  style: GoogleFonts.oswald(
                                    fontSize: 12,
                                    fontWeight: FontWeight.bold,
                                    letterSpacing: 2.5,
                                    color: AppColors.accent,
                                  ),
                                )
                                .animate()
                                .fadeIn(duration: 400.ms)
                                .slideX(
                                  begin: -0.1,
                                  end: 0,
                                  curve: Curves.easeOutCubic,
                                ),
                            const SizedBox(height: 4),
                            Text(
                                  user != null
                                      ? user.firstName
                                      : "WELCOME BACK",
                                  style: GoogleFonts.oswald(
                                    fontSize: 26,
                                    fontWeight: FontWeight.w900,
                                    height: 1.1,
                                    letterSpacing: 1.0,
                                    color: AppColors.textPrimary,
                                  ),
                                  overflow: TextOverflow.ellipsis,
                                )
                                .animate(delay: 80.ms)
                                .fadeIn(duration: 400.ms)
                                .slideX(
                                  begin: -0.1,
                                  end: 0,
                                  curve: Curves.easeOutCubic,
                                ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 12),
                      GestureDetector(
                        onTap: () =>
                            widget.onNavigateToTab(4), // Go to Profile tab
                        child: _Avatar(user: user)
                            .animate()
                            .fadeIn(duration: 400.ms)
                            .scale(
                              begin: const Offset(0.6, 0.6),
                              curve: Curves.easeOutBack,
                              duration: 450.ms,
                            ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  if (nextUp != null) ...[
                    GestureDetector(
                          onTap: () => widget.onNavigateToTab(2),
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 12,
                              vertical: 10,
                            ),
                            decoration: BoxDecoration(
                              color: AppColors.bgCard.withOpacity(0.85),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: AppColors.border),
                            ),
                            child: Row(
                              children: [
                                const Icon(
                                  Icons.bolt,
                                  color: AppColors.accent,
                                  size: 18,
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        "NEXT UP · ${nextUp.day.shortLabel} ${nextUp.startTime.label}",
                                        style: GoogleFonts.oswald(
                                          fontSize: 10,
                                          fontWeight: FontWeight.bold,
                                          letterSpacing: 1.0,
                                          color: AppColors.textMuted,
                                        ),
                                      ),
                                      Text(
                                        nextUp.title,
                                        style: GoogleFonts.inter(
                                          fontSize: 13,
                                          fontWeight: FontWeight.w600,
                                          color: AppColors.textPrimary,
                                        ),
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                    ],
                                  ),
                                ),
                                const Icon(
                                  Icons.chevron_right,
                                  color: AppColors.textMuted,
                                  size: 18,
                                ),
                              ],
                            ),
                          ),
                        )
                        .animate(delay: 180.ms)
                        .fadeIn(duration: 400.ms)
                        .slideX(begin: 0.1, end: 0, curve: Curves.easeOutCubic),
                    const SizedBox(height: 12),
                  ],
                  Wrap(
                        spacing: 10,
                        runSpacing: 10,
                        children: [
                          SlantedButton(
                            text: "BROWSE WORKOUTS",
                            icon: Icons.arrow_forward,
                            paddingVertical: 10,
                            paddingHorizontal: 18,
                            onPressed: () => widget.onNavigateToTab(1),
                          ),
                          SlantedButton(
                            text: "MY TIMETABLE",
                            isSecondary: true,
                            paddingVertical: 10,
                            paddingHorizontal: 18,
                            onPressed: () => widget.onNavigateToTab(2),
                          ),
                        ],
                      )
                      .animate(delay: 260.ms)
                      .fadeIn(duration: 400.ms)
                      .slideY(begin: 0.15, end: 0, curve: Curves.easeOutCubic),
                ],
              ),
            ),
          ],
        ),
      ),
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
          child: LiquidGlassContainer(
            borderRadius: BorderRadius.circular(16),
            padding: const EdgeInsets.symmetric(vertical: 18, horizontal: 12),
            border: Border.all(color: AppColors.borderAccent),
            boxShadow: const [
              BoxShadow(
                color: AppColors.shadowAccent,
                blurRadius: 15,
                spreadRadius: 1,
              ),
            ],
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
                                final isDecimalFree =
                                    value == value.roundToDouble();
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
                    const _AccentUnderline(),
                    const SizedBox(height: 4),
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
          _FeaturedWorkoutsCarousel(workouts: featured),
      ],
    );
  }

  Widget _buildWhyUsSection() {
    final features = [
      {
        'icon': Icons.fitness_center,
        'title': 'Modern Equipment',
        'desc': 'State of the art resistance & cardio machinery.',
      },
      {
        'icon': Icons.military_tech,
        'title': 'Elite Trainers',
        'desc': 'Certified coaches dedicated to your success.',
      },
      {
        'icon': Icons.bolt,
        'title': 'Customized Programs',
        'desc': 'Tailored workouts for your specific goals.',
      },
      {
        'icon': Icons.groups,
        'title': 'Dynamic Community',
        'desc': 'Supportive atmosphere that motivates daily.',
      },
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
          const _AccentUnderline(),
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
          child: ClipRRect(
            borderRadius: BorderRadius.circular(16),
            child: Stack(
              children: [
                Positioned.fill(
                  child: Image.asset(
                    'assets/images/strength_training.png',
                    fit: BoxFit.cover,
                    opacity: const AlwaysStoppedAnimation(0.3),
                    errorBuilder: (context, error, stackTrace) =>
                        Container(color: AppColors.bgSecondary),
                  ),
                ),
                LiquidGlassContainer(
                  borderRadius: BorderRadius.circular(16),
                  padding: const EdgeInsets.all(24),
                  tint: AppColors.bgSecondary,
                  border: Border.all(color: AppColors.borderAccent),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const OutlineText(text: "KEEP PUSHING", fontSize: 22),
                      Text(
                        "FORWARD, EVERY DAY",
                        style: GoogleFonts.oswald(
                          fontSize: 24,
                          fontWeight: FontWeight.w900,
                          color: AppColors.accent,
                        ),
                      ),
                      const SizedBox(height: 10),
                      Text(
                        "Explore new classes and keep building your fitness journey with VitroFit.",
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
                            text: "BROWSE WORKOUTS",
                            icon: Icons.flash_on,
                            onPressed: () =>
                                widget.onNavigateToTab(1), // Go to Workouts tab
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
                ),
              ],
            ),
          ),
        )
        .animate()
        .fadeIn(duration: 500.ms)
        .slideY(begin: 0.1, end: 0, curve: Curves.easeOutCubic);
  }
}

/// A slim accent bar under a section headline that draws itself in on entrance.
class _AccentUnderline extends StatelessWidget {
  const _AccentUnderline();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 6),
      child: TweenAnimationBuilder<double>(
        tween: Tween(begin: 0, end: 1),
        duration: const Duration(milliseconds: 500),
        curve: Curves.easeOutCubic,
        builder: (context, value, child) {
          return Align(
            alignment: Alignment.centerLeft,
            child: FractionallySizedBox(
              widthFactor: value,
              child: Container(
                height: 3,
                width: 46,
                decoration: BoxDecoration(
                  color: AppColors.accent,
                  borderRadius: BorderRadius.circular(2),
                  boxShadow: const [
                    BoxShadow(color: AppColors.shadowAccent, blurRadius: 8),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

/// Horizontal workout carousel where the card nearest the viewport center
/// scales up slightly and dims the others, for a modern "focus" feel while scrolling.
class _FeaturedWorkoutsCarousel extends StatefulWidget {
  final List<Workout> workouts;

  const _FeaturedWorkoutsCarousel({required this.workouts});

  @override
  State<_FeaturedWorkoutsCarousel> createState() =>
      _FeaturedWorkoutsCarouselState();
}

class _FeaturedWorkoutsCarouselState extends State<_FeaturedWorkoutsCarousel> {
  final _controller = ScrollController();
  static const double _cardWidth = 240;
  static const double _cardMargin = 16;

  @override
  void initState() {
    super.initState();
    _controller.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final viewportWidth = MediaQuery.of(context).size.width;
    final offset = _controller.hasClients ? _controller.offset : 0.0;

    return SizedBox(
      height: 230,
      child: ListView.builder(
        controller: _controller,
        padding: const EdgeInsets.symmetric(horizontal: 20),
        scrollDirection: Axis.horizontal,
        itemCount: widget.workouts.length,
        itemBuilder: (context, index) {
          final item = widget.workouts[index];
          final cardCenter =
              20 + index * (_cardWidth + _cardMargin) + _cardWidth / 2;
          final viewportCenter = offset + viewportWidth / 2;
          final distance = (cardCenter - viewportCenter).abs();
          final t = (1 - (distance / (viewportWidth * 0.7))).clamp(0.0, 1.0);
          final scale = 0.92 + 0.08 * t;
          final opacity = 0.65 + 0.35 * t;

          return Container(
                width: _cardWidth,
                margin: const EdgeInsets.only(right: _cardMargin),
                child: Opacity(
                  opacity: opacity,
                  child: Transform.scale(
                    scale: scale,
                    child: WorkoutCard(
                      workout: item,
                      onTap: () => WorkoutDetailSheet.show(context, item),
                    ),
                  ),
                ),
              )
              .animate(delay: (index * 80).ms)
              .fadeIn(duration: 350.ms)
              .slideX(begin: 0.15, end: 0, curve: Curves.easeOut);
        },
      ),
    );
  }
}

class _Avatar extends StatelessWidget {
  final UserProfile? user;

  const _Avatar({required this.user});

  @override
  Widget build(BuildContext context) {
    final imageUrl = user?.profileImageUrl;
    return Container(
      width: 48,
      height: 48,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [AppColors.accent.withOpacity(0.9), AppColors.accentDark],
        ),
        border: Border.all(color: AppColors.bgPrimary, width: 2),
        boxShadow: const [
          BoxShadow(
            color: AppColors.shadowAccent,
            blurRadius: 10,
            spreadRadius: 1,
          ),
        ],
        image: imageUrl != null
            ? DecorationImage(image: NetworkImage(imageUrl), fit: BoxFit.cover)
            : null,
      ),
      alignment: Alignment.center,
      child: imageUrl == null
          ? Text(
              user?.initials ?? "?",
              style: GoogleFonts.oswald(
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: AppColors.bgPrimary,
              ),
            )
          : null,
    );
  }
}

class _WhyUsCard extends StatefulWidget {
  final IconData icon;
  final String title;
  final String desc;

  const _WhyUsCard({
    required this.icon,
    required this.title,
    required this.desc,
  });

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
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: _pressed ? AppColors.accent : Colors.transparent,
              width: _pressed ? 1.5 : 0,
            ),
          ),
          child: LiquidGlassContainer(
            borderRadius: BorderRadius.circular(14),
            padding: const EdgeInsets.all(14),
            blur: false,
            boxShadow: _pressed
                ? const [
                    BoxShadow(
                      color: AppColors.shadowAccent,
                      blurRadius: 14,
                      spreadRadius: 1,
                    ),
                  ]
                : const [],
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
                      colors: [
                        AppColors.accent.withOpacity(0.22),
                        AppColors.accent.withOpacity(0.06),
                      ],
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
      ),
    );
  }
}
