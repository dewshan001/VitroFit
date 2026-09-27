import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:geolocator/geolocator.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:latlong2/latlong.dart' hide Path;
import 'package:url_launcher/url_launcher.dart';

import '../api/geoapify_api.dart';
import '../api/gym_agent_api.dart';
import '../models/gym.dart';
import '../models/gym_details.dart';
import '../models/workout_suggestion.dart';
import '../theme/app_theme.dart';
import '../widgets/badge_chip.dart';
import '../widgets/outline_text.dart';
import '../widgets/skeleton_box.dart';
import '../widgets/slanted_button.dart';

const LatLng _fallbackCenter = LatLng(6.9271, 79.8612); // Colombo, matches the website's default
const int _pageSize = 5;

class FindGymScreen extends StatefulWidget {
  const FindGymScreen({super.key});

  @override
  State<FindGymScreen> createState() => _FindGymScreenState();
}

class _FindGymScreenState extends State<FindGymScreen> {
  final _geoapifyApi = GeoapifyApi();
  final _gymAgentApi = GymAgentApi();
  final _mapController = MapController();

  LatLng? _userLocation;
  bool _locating = true;
  bool _usingFallback = false;
  bool _mapReady = false;

  List<Gym> _gyms = [];
  bool _searching = false;
  String? _searchError;
  int _visibleCount = _pageSize;

  Timer? _panDebounce;

  final Map<String, GymDetails> _detailsCache = {};
  final Set<String> _detailsLoading = {};
  final Map<String, WorkoutSuggestionsResult> _workoutCache = {};

  @override
  void initState() {
    super.initState();
    _locateAndSearch();
  }

  @override
  void dispose() {
    _panDebounce?.cancel();
    super.dispose();
  }

  Future<void> _locateAndSearch() async {
    setState(() => _locating = true);
    LatLng center = _fallbackCenter;
    var fallback = true;

    try {
      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission != LocationPermission.denied && permission != LocationPermission.deniedForever) {
        final serviceEnabled = await Geolocator.isLocationServiceEnabled();
        if (serviceEnabled) {
          final position = await Geolocator.getCurrentPosition(
            locationSettings: const LocationSettings(accuracy: LocationAccuracy.high, timeLimit: Duration(seconds: 8)),
          );
          center = LatLng(position.latitude, position.longitude);
          fallback = false;
        }
      }
    } catch (_) {
      // Falls back to the default center below, same as the website's behavior.
    }

    if (!mounted) return;
    setState(() {
      _userLocation = fallback ? null : center;
      _usingFallback = fallback;
      _locating = false;
    });
    if (_mapReady) _mapController.move(center, 13);
    await _fetchGyms(center);
  }

  Future<void> _fetchGyms(LatLng center) async {
    setState(() {
      _searching = true;
      _searchError = null;
    });
    try {
      final gyms = await _geoapifyApi.searchNearby(lat: center.latitude, lng: center.longitude);
      gyms.sort((a, b) => (a.distanceMeters ?? double.infinity).compareTo(b.distanceMeters ?? double.infinity));
      if (!mounted) return;
      setState(() {
        _gyms = gyms;
        _visibleCount = _pageSize;
        _searching = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _searching = false;
        _searchError = 'Could not load nearby gyms. Check your connection and try again.';
      });
    }
  }

  void _onMapPositionChanged(MapCamera camera, bool hasGesture) {
    if (!hasGesture) return;
    _panDebounce?.cancel();
    _panDebounce = Timer(const Duration(milliseconds: 300), () => _fetchGyms(camera.center));
  }

  Future<void> _ensureDetails(Gym gym, {int delayMs = 0}) async {
    if (_detailsCache.containsKey(gym.placeId) || _detailsLoading.contains(gym.placeId)) return;
    _detailsLoading.add(gym.placeId);
    if (delayMs > 0) await Future.delayed(Duration(milliseconds: delayMs));
    if (!mounted) return;
    try {
      final details = await _gymAgentApi.getDetails(gym);
      if (!mounted) return;
      setState(() => _detailsCache[gym.placeId] = details);
    } catch (_) {
      // Silently skip - the card/sheet just shows without enrichment.
    } finally {
      _detailsLoading.remove(gym.placeId);
    }
  }

  Future<void> _openDirections(Gym gym) async {
    final uri = Uri.parse('https://www.google.com/maps/dir/?api=1&destination=${gym.lat},${gym.lng}');
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  Future<void> _showWorkoutSuggestions(Gym gym) async {
    await _ensureDetails(gym);
    if (!mounted) return;
    final details = _detailsCache[gym.placeId] ?? const GymDetails(placeId: '', source: 'ai-generic', equipment: [], classes: []);

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => _WorkoutSuggestionsSheet(
        gym: gym,
        details: details,
        cached: _workoutCache[gym.placeId],
        onLoad: () async {
          final cached = _workoutCache[gym.placeId];
          if (cached != null) return cached;
          final result = await _gymAgentApi.getWorkoutSuggestions(details, gym.name);
          _workoutCache[gym.placeId] = result;
          return result;
        },
      ),
    );
  }

  void _showGymSheet(Gym gym) {
    _ensureDetails(gym);
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => StatefulBuilder(
        builder: (context, setSheetState) {
          return _GymDetailSheet(
            gym: gym,
            details: _detailsCache[gym.placeId],
            onDirections: () => _openDirections(gym),
            onFindWorkouts: () => _showWorkoutSuggestions(gym),
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final visible = _gyms.take(_visibleCount).toList();
    final statusText = _locating
        ? "Detecting your location…"
        : _usingFallback
            ? "Default area • ${_gyms.length} places found"
            : "Location active • ${_gyms.length} places found";

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: RefreshIndicator(
        color: AppColors.accent,
        backgroundColor: AppColors.bgCard,
        onRefresh: () => _fetchGyms(_userLocation ?? _fallbackCenter),
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(parent: BouncingScrollPhysics()),
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 100),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const OutlineText(text: "FIND YOUR", fontSize: 24),
              Text(
                "NEAREST GYM",
                style: GoogleFonts.oswald(fontSize: 32, fontWeight: FontWeight.bold, letterSpacing: 1.5, color: AppColors.accent),
              ),
              const SizedBox(height: 6),
              Text(
                "Discover fitness centres near you, with AI-suggested workouts for each one.",
                style: GoogleFonts.inter(fontSize: 13, color: AppColors.textSecondary),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Icon(
                    _locating ? Icons.my_location : (_usingFallback ? Icons.location_disabled : Icons.location_on),
                    size: 14,
                    color: AppColors.accent,
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(statusText, style: GoogleFonts.inter(fontSize: 12, color: AppColors.textSecondary)),
                  ),
                  if (_searching)
                    const SizedBox(
                      width: 12,
                      height: 12,
                      child: CircularProgressIndicator(strokeWidth: 2, valueColor: AlwaysStoppedAnimation(AppColors.accent)),
                    ),
                ],
              ),
              const SizedBox(height: 12),
              _buildMap(),
              const SizedBox(height: 10),
              _buildLegend(),
              const SizedBox(height: 24),
              Text(
                "GYM LIST",
                style: GoogleFonts.oswald(fontSize: 18, fontWeight: FontWeight.bold, letterSpacing: 1.0, color: AppColors.textPrimary),
              ),
              const SizedBox(height: 12),
              _buildList(visible),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildMap() {
    return Container(
      height: 320,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.borderAccent),
        boxShadow: const [BoxShadow(color: AppColors.shadowAccent, blurRadius: 16, spreadRadius: 1)],
      ),
      clipBehavior: Clip.antiAlias,
      child: FlutterMap(
        mapController: _mapController,
        options: MapOptions(
          initialCenter: _fallbackCenter,
          initialZoom: 12,
          onMapReady: () {
            _mapReady = true;
            if (_userLocation != null) _mapController.move(_userLocation!, 13);
          },
          onPositionChanged: _onMapPositionChanged,
        ),
        children: [
          TileLayer(
            urlTemplate: 'https://maps.geoapify.com/v1/tile/dark-matter/{z}/{x}/{y}.png?apiKey=${_geoapifyApiKeyForTiles()}',
            userAgentPackageName: 'com.vitrofit.mobile',
          ),
          MarkerLayer(
            markers: [
              if (_userLocation != null)
                Marker(
                  point: _userLocation!,
                  width: 40,
                  height: 40,
                  child: const _UserPulseMarker(),
                ),
              ..._gyms.map(
                (gym) => Marker(
                  point: LatLng(gym.lat, gym.lng),
                  width: 36,
                  height: 42,
                  alignment: Alignment.topCenter,
                  child: GestureDetector(
                    onTap: () => _showGymSheet(gym),
                    child: const _GymPin(),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildLegend() {
    return Row(
      children: [
        Container(width: 10, height: 10, decoration: const BoxDecoration(color: AppColors.info, shape: BoxShape.circle)),
        const SizedBox(width: 6),
        Text("Your location", style: GoogleFonts.inter(fontSize: 11, color: AppColors.textMuted)),
        const SizedBox(width: 16),
        const Icon(Icons.fitness_center, size: 12, color: AppColors.accent),
        const SizedBox(width: 6),
        Text("Gym • tap for details", style: GoogleFonts.inter(fontSize: 11, color: AppColors.textMuted)),
      ],
    );
  }

  Widget _buildList(List<Gym> visible) {
    if (_searching && _gyms.isEmpty) {
      return Column(
        children: List.generate(3, (i) => const Padding(padding: EdgeInsets.only(bottom: 14), child: SkeletonBox(height: 130, borderRadius: 14))),
      );
    }
    if (_searchError != null && _gyms.isEmpty) {
      return _emptyCard(Icons.wifi_off, _searchError!);
    }
    if (_gyms.isEmpty) {
      return _emptyCard(Icons.location_off, "No gyms found nearby.");
    }

    return Column(
      children: [
        ...List.generate(visible.length, (index) {
          final gym = visible[index];
          return Padding(
            padding: const EdgeInsets.only(bottom: 14),
            child: _GymCard(
              gym: gym,
              details: _detailsCache[gym.placeId],
              onVisible: () => _ensureDetails(gym, delayMs: index * 600),
              onDirections: () => _openDirections(gym),
              onFindWorkouts: () => _showWorkoutSuggestions(gym),
              onTap: () => _showGymSheet(gym),
            ).animate(delay: (index * 60).ms).fadeIn(duration: 300.ms).slideY(begin: 0.08, end: 0, curve: Curves.easeOut),
          );
        }),
        if (_visibleCount < _gyms.length)
          SizedBox(
            width: double.infinity,
            child: SlantedButton(
              text: "LOAD MORE",
              isSecondary: true,
              onPressed: () => setState(() => _visibleCount += _pageSize),
            ),
          ),
      ],
    );
  }

  Widget _emptyCard(IconData icon, String message) {
    return Container(
      padding: const EdgeInsets.all(40),
      width: double.infinity,
      decoration: BoxDecoration(color: AppColors.bgCard, borderRadius: BorderRadius.circular(12)),
      child: Column(
        children: [
          Icon(icon, size: 40, color: AppColors.textMuted),
          const SizedBox(height: 12),
          Text(message, style: GoogleFonts.inter(color: AppColors.textSecondary), textAlign: TextAlign.center),
        ],
      ),
    );
  }

  String _geoapifyApiKeyForTiles() => const String.fromEnvironment('GEOAPIFY_API_KEY', defaultValue: 'df0e01be60a848199b726c73604f3280');
}

class _UserPulseMarker extends StatelessWidget {
  const _UserPulseMarker();

  @override
  Widget build(BuildContext context) {
    return Stack(
      alignment: Alignment.center,
      children: [
        Container(width: 40, height: 40, decoration: const BoxDecoration(shape: BoxShape.circle, color: AppColors.info))
            .animate(onPlay: (c) => c.repeat())
            .scaleXY(begin: 0.4, end: 1.0, duration: 1600.ms, curve: Curves.easeOut)
            .fadeOut(duration: 1600.ms, curve: Curves.easeOut, begin: 0.5),
        Container(
          width: 16,
          height: 16,
          decoration: BoxDecoration(shape: BoxShape.circle, color: AppColors.info, border: Border.all(color: Colors.white, width: 2)),
        ),
      ],
    );
  }
}

class _GymPin extends StatelessWidget {
  const _GymPin();

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 30,
          height: 30,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: const LinearGradient(colors: [AppColors.accent, AppColors.accentDark]),
            boxShadow: const [BoxShadow(color: AppColors.shadowAccent, blurRadius: 6)],
          ),
          child: const Icon(Icons.fitness_center, size: 15, color: AppColors.bgPrimary),
        ),
        CustomPaint(size: const Size(8, 6), painter: _PinTailPainter()),
      ],
    );
  }
}

class _PinTailPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final path = Path()
      ..moveTo(0, 0)
      ..lineTo(size.width, 0)
      ..lineTo(size.width / 2, size.height)
      ..close();
    canvas.drawPath(path, Paint()..color = AppColors.accentDark);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _GymCard extends StatefulWidget {
  final Gym gym;
  final GymDetails? details;
  final VoidCallback onVisible;
  final VoidCallback onDirections;
  final VoidCallback onFindWorkouts;
  final VoidCallback onTap;

  const _GymCard({
    required this.gym,
    required this.details,
    required this.onVisible,
    required this.onDirections,
    required this.onFindWorkouts,
    required this.onTap,
  });

  @override
  State<_GymCard> createState() => _GymCardState();
}

class _GymCardState extends State<_GymCard> {
  @override
  void initState() {
    super.initState();
    widget.onVisible();
  }

  @override
  Widget build(BuildContext context) {
    final gym = widget.gym;
    final details = widget.details;

    return GestureDetector(
      onTap: widget.onTap,
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.bgCard,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: AppColors.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    gym.name,
                    style: GoogleFonts.oswald(fontSize: 17, fontWeight: FontWeight.bold, color: AppColors.textPrimary),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                if (gym.distanceMeters != null) ...[
                  const SizedBox(width: 8),
                  BadgeChip(label: "${gym.distanceKm.toStringAsFixed(1)} KM", isAccent: true),
                ],
              ],
            ),
            if (gym.address != null) ...[
              const SizedBox(height: 4),
              Text(gym.address!, style: GoogleFonts.inter(fontSize: 12, color: AppColors.textSecondary), maxLines: 2, overflow: TextOverflow.ellipsis),
            ],
            const SizedBox(height: 10),
            if (details == null)
              const SkeletonBox(height: 22, borderRadius: 6)
            else if (details.equipment.isNotEmpty || details.classes.isNotEmpty)
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: [
                  ...details.equipment.take(4).map((e) => BadgeChip(label: e, isAccent: false)),
                  ...details.classes.take(2).map((e) => BadgeChip(label: e, isAccent: false)),
                ],
              ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: widget.onDirections,
                    style: OutlinedButton.styleFrom(side: const BorderSide(color: AppColors.border), padding: const EdgeInsets.symmetric(vertical: 10)),
                    icon: const Icon(Icons.directions, size: 16, color: AppColors.accent),
                    label: Text("DIRECTIONS", style: GoogleFonts.oswald(fontSize: 12, color: AppColors.textPrimary, fontWeight: FontWeight.bold)),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: widget.onFindWorkouts,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.accent,
                      padding: const EdgeInsets.symmetric(vertical: 10),
                      elevation: 0,
                    ),
                    icon: const Icon(Icons.auto_awesome, size: 16, color: AppColors.bgPrimary),
                    label: Text("WORKOUTS", style: GoogleFonts.oswald(fontSize: 12, color: AppColors.bgPrimary, fontWeight: FontWeight.bold)),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _GymDetailSheet extends StatelessWidget {
  final Gym gym;
  final GymDetails? details;
  final VoidCallback onDirections;
  final VoidCallback onFindWorkouts;

  const _GymDetailSheet({required this.gym, required this.details, required this.onDirections, required this.onFindWorkouts});

  Future<void> _launch(String scheme, String value) async {
    await launchUrl(Uri.parse('$scheme:$value'));
  }

  Future<void> _launchWebsite(String url) async {
    final normalized = url.startsWith('http') ? url : 'https://$url';
    await launchUrl(Uri.parse(normalized), mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: Container(
        decoration: const BoxDecoration(
          color: AppColors.bgPrimary,
          borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          border: Border(top: BorderSide(color: AppColors.accent, width: 2)),
        ),
        clipBehavior: Clip.antiAlias,
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(color: AppColors.textMuted, borderRadius: BorderRadius.circular(2)),
                ),
              ),
              Text(gym.name, style: GoogleFonts.oswald(fontSize: 22, fontWeight: FontWeight.bold, color: AppColors.accent)),
              if (gym.distanceMeters != null) ...[
                const SizedBox(height: 4),
                Text("${gym.distanceKm.toStringAsFixed(1)} km away", style: GoogleFonts.inter(fontSize: 12, color: AppColors.textMuted)),
              ],
              if (gym.address != null) ...[
                const SizedBox(height: 10),
                Text(gym.address!, style: GoogleFonts.inter(fontSize: 13, color: AppColors.textSecondary)),
              ],
              const SizedBox(height: 16),
              if (details == null)
                const SkeletonBox(height: 60, borderRadius: 10)
              else ...[
                if (details!.equipment.isNotEmpty) ...[
                  Text("EQUIPMENT", style: GoogleFonts.oswald(fontSize: 12, fontWeight: FontWeight.bold, color: AppColors.textPrimary, letterSpacing: 1.0)),
                  const SizedBox(height: 8),
                  Wrap(spacing: 6, runSpacing: 6, children: details!.equipment.map((e) => BadgeChip(label: e, isAccent: false)).toList()),
                  const SizedBox(height: 12),
                ],
                if (details!.classes.isNotEmpty) ...[
                  Text("CLASSES", style: GoogleFonts.oswald(fontSize: 12, fontWeight: FontWeight.bold, color: AppColors.textPrimary, letterSpacing: 1.0)),
                  const SizedBox(height: 8),
                  Wrap(spacing: 6, runSpacing: 6, children: details!.classes.map((e) => BadgeChip(label: e, isAccent: true)).toList()),
                  const SizedBox(height: 12),
                ],
                if (details!.openingHours != null) _infoRow(Icons.schedule, details!.openingHours!),
                if (details!.phone != null)
                  GestureDetector(onTap: () => _launch('tel', details!.phone!), child: _infoRow(Icons.call, details!.phone!, accent: true)),
                if (details!.email != null)
                  GestureDetector(onTap: () => _launch('mailto', details!.email!), child: _infoRow(Icons.email_outlined, details!.email!, accent: true)),
                if (gym.website != null)
                  GestureDetector(onTap: () => _launchWebsite(gym.website!), child: _infoRow(Icons.language, gym.website!, accent: true)),
              ],
              const SizedBox(height: 20),
              Row(
                children: [
                  Expanded(
                    child: SlantedButton(text: "DIRECTIONS", icon: Icons.directions, isSecondary: true, onPressed: onDirections),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: SlantedButton(text: "WORKOUTS", icon: Icons.auto_awesome, onPressed: onFindWorkouts),
                  ),
                ],
              ),
              const SizedBox(height: 8),
            ],
          ),
        ),
      ),
    );
  }

  Widget _infoRow(IconData icon, String text, {bool accent = false}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          Icon(icon, size: 16, color: accent ? AppColors.accent : AppColors.textMuted),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              text,
              style: GoogleFonts.inter(fontSize: 13, color: accent ? AppColors.accent : AppColors.textSecondary),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }
}

class _WorkoutSuggestionsSheet extends StatefulWidget {
  final Gym gym;
  final GymDetails details;
  final WorkoutSuggestionsResult? cached;
  final Future<WorkoutSuggestionsResult> Function() onLoad;

  const _WorkoutSuggestionsSheet({required this.gym, required this.details, required this.cached, required this.onLoad});

  @override
  State<_WorkoutSuggestionsSheet> createState() => _WorkoutSuggestionsSheetState();
}

class _WorkoutSuggestionsSheetState extends State<_WorkoutSuggestionsSheet> {
  WorkoutSuggestionsResult? _result;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _result = widget.cached;
    if (_result != null) {
      _loading = false;
    } else {
      _load();
    }
  }

  Future<void> _load() async {
    try {
      final result = await widget.onLoad();
      if (mounted) {
        setState(() {
          _result = result;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _loading = false;
          _error = e.toString();
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: Container(
        constraints: BoxConstraints(maxHeight: MediaQuery.of(context).size.height * 0.85),
        decoration: const BoxDecoration(
          color: AppColors.bgPrimary,
          borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          border: Border(top: BorderSide(color: AppColors.accent, width: 2)),
        ),
        clipBehavior: Clip.antiAlias,
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(color: AppColors.textMuted, borderRadius: BorderRadius.circular(2)),
                ),
              ),
              Row(
                children: [
                  const Icon(Icons.auto_awesome, color: AppColors.accent, size: 20),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      "AI WORKOUTS · ${widget.gym.name}",
                      style: GoogleFonts.oswald(fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.accent),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              if (_loading)
                Column(
                  children: List.generate(2, (i) => const Padding(padding: EdgeInsets.only(bottom: 12), child: SkeletonBox(height: 100, borderRadius: 12))),
                )
              else if (_error != null)
                Text(_error!, style: GoogleFonts.inter(color: AppColors.error))
              else if (_result != null) ...[
                ..._result!.workouts.map((w) => _WorkoutCard(workout: w)),
                if (_result!.notes != null) ...[
                  const SizedBox(height: 4),
                  Text(_result!.notes!, style: GoogleFonts.inter(fontSize: 11, color: AppColors.textMuted, fontStyle: FontStyle.italic)),
                ],
              ],
              const SizedBox(height: 8),
            ],
          ),
        ),
      ),
    );
  }
}

class _WorkoutCard extends StatelessWidget {
  final WorkoutSuggestion workout;
  const _WorkoutCard({required this.workout});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: AppColors.bgCard, borderRadius: BorderRadius.circular(12), border: Border.all(color: AppColors.border)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(workout.name, style: GoogleFonts.oswald(fontSize: 16, fontWeight: FontWeight.bold, color: AppColors.textPrimary)),
              ),
              Text("${workout.durationMinutes} MIN", style: GoogleFonts.inter(fontSize: 11, color: AppColors.textMuted, fontWeight: FontWeight.bold)),
            ],
          ),
          const SizedBox(height: 6),
          Wrap(
            spacing: 6,
            children: [
              BadgeChip(label: workout.category, isAccent: true),
              BadgeChip(label: workout.difficulty, isAccent: false),
            ],
          ),
          if (workout.description.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(workout.description, style: GoogleFonts.inter(fontSize: 12.5, color: AppColors.textSecondary)),
          ],
          if (workout.equipmentUsed.isNotEmpty) ...[
            const SizedBox(height: 8),
            Wrap(
              spacing: 4,
              runSpacing: 4,
              children: workout.equipmentUsed
                  .map((e) => Text("• $e", style: GoogleFonts.inter(fontSize: 11, color: AppColors.textMuted)))
                  .toList(),
            ),
          ],
        ],
      ),
    );
  }
}
