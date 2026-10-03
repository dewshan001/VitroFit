import 'dart:async';

import 'package:flutter/foundation.dart' show Factory;
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:geolocator/geolocator.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:url_launcher/url_launcher.dart';

import '../api/google_places_api.dart';
import '../api/gym_agent_api.dart';
import '../models/gym.dart';
import '../models/gym_details.dart';
import '../models/workout_suggestion.dart';
import '../theme/app_theme.dart';
import '../widgets/badge_chip.dart';
import '../widgets/liquid_glass.dart';
import '../widgets/map_marker_icons.dart';
import '../widgets/outline_text.dart';
import '../widgets/skeleton_box.dart';
import '../widgets/slanted_button.dart';

const LatLng _fallbackCenter = LatLng(
  6.9271,
  79.8612,
); // Colombo, matches the website's default
const int _pageSize = 5;

class FindGymScreen extends StatefulWidget {
  const FindGymScreen({super.key});

  @override
  State<FindGymScreen> createState() => _FindGymScreenState();
}

class _FindGymScreenState extends State<FindGymScreen>
    with TickerProviderStateMixin {
  final _placesApi = GooglePlacesApi();
  final _gymAgentApi = GymAgentApi();
  GoogleMapController? _mapController;
  BitmapDescriptor? _gymIcon;
  BitmapDescriptor? _userIcon;
  bool _iconsRequested = false;
  final _searchController = TextEditingController();

  LatLng? _userLocation;
  bool _locating = true;
  bool _usingFallback = false;
  bool _mapReady = false;

  /// Why location resolution fell back, if it did - shown in the UI so this
  /// is diagnosable without a console (permission/service/GPS all collapse
  /// to the same "using fallback" state otherwise).
  String? _locationIssue;
  bool _locationPermissionBlocked = false;

  /// The camera as last reported by the map; a re-search uses its centre.
  LatLng _cameraCenter = _fallbackCenter;

  /// Set while the app itself moves the camera, so the resulting "camera idle"
  /// does not trigger a second search for the same spot.
  bool _programmaticMove = false;

  List<Gym> _gyms = [];
  bool _searching = false;
  String? _searchError;
  int _visibleCount = _pageSize;
  String _searchQuery = '';

  Timer? _panDebounce;

  final Map<String, GymDetails> _detailsCache = {};
  final Set<String> _detailsLoading = {};
  final Set<String> _detailsFailed = {};
  final Map<String, WorkoutSuggestionsResult> _workoutCache = {};

  @override
  void initState() {
    super.initState();
    // Defer to after the first frame: this screen is built immediately at
    // app startup (it lives inside an IndexedStack that builds all tabs
    // eagerly), and requesting the location permission before the Activity
    // has settled can make the OS silently skip showing its dialog.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _locateAndSearch();
    });
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_iconsRequested) {
      _iconsRequested = true;
      _loadMarkerIcons(MediaQuery.devicePixelRatioOf(context));
    }
  }

  @override
  void dispose() {
    _panDebounce?.cancel();
    _mapController?.dispose();
    _searchController.dispose();
    super.dispose();
  }

  /// Smoothly moves the map to [target].
  ///
  /// Never allowed to throw: a camera failure must not be able to break the
  /// caller's control flow (in particular `_locateAndSearch`, where this is
  /// called right before the gym fetch).
  void _animateCameraTo(LatLng target, double zoom) {
    _cameraCenter = target;
    final controller = _mapController;
    if (controller == null) return;
    _programmaticMove = true;
    controller
        .animateCamera(CameraUpdate.newLatLngZoom(target, zoom))
        .catchError((_) {
          _programmaticMove = false;
        });
  }

  /// Draws the pin and "you are here" bitmaps once (they depend on the
  /// screen's pixel ratio).
  Future<void> _loadMarkerIcons(double pixelRatio) async {
    final gym = await MapMarkerIcons.gymPin(pixelRatio: pixelRatio);
    final user = await MapMarkerIcons.userDot(pixelRatio: pixelRatio);
    if (!mounted) return;
    setState(() {
      _gymIcon = gym;
      _userIcon = user;
    });
  }

  Future<void> _locateAndSearch() async {
    setState(() {
      _locating = true;
      _locationIssue = null;
      _locationPermissionBlocked = false;
    });
    LatLng center = _fallbackCenter;
    var fallback = true;
    String? issue;
    var permissionBlocked = false;

    try {
      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.denied) {
        issue = "Location permission denied.";
      } else if (permission == LocationPermission.deniedForever) {
        issue = "Location permission blocked — enable it in Settings.";
        permissionBlocked = true;
      } else {
        final serviceEnabled = await Geolocator.isLocationServiceEnabled();
        if (!serviceEnabled) {
          issue = "Location services are turned off.";
        } else {
          final position = await Geolocator.getCurrentPosition(
            locationSettings: const LocationSettings(
              accuracy: LocationAccuracy.high,
              timeLimit: Duration(seconds: 8),
            ),
          );
          center = LatLng(position.latitude, position.longitude);
          fallback = false;
        }
      }
    } catch (_) {
      // Falls back to the default center below, same as the website's behavior.
      issue = "Couldn't get your location.";
    }

    if (!mounted) return;
    setState(() {
      _userLocation = fallback ? null : center;
      _usingFallback = fallback;
      _locating = false;
      _locationIssue = fallback ? issue : null;
      _locationPermissionBlocked = permissionBlocked;
    });
    try {
      if (_mapReady) _animateCameraTo(center, 13);
    } catch (_) {
      // Camera animation is cosmetic; never let it block loading gyms.
    }
    await _fetchGyms(center);
  }

  Future<void> _fetchGyms(LatLng center) async {
    setState(() {
      _searching = true;
      _searchError = null;
    });
    try {
      final gyms = await _placesApi.searchNearby(
        lat: center.latitude,
        lng: center.longitude,
      );
      gyms.sort(
        (a, b) => (a.distanceMeters ?? double.infinity).compareTo(
          b.distanceMeters ?? double.infinity,
        ),
      );
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
        _searchError = e is GooglePlacesException
            ? 'Could not load nearby gyms: ${e.message}'
            : 'Could not load nearby gyms. Check your connection and try again.';
      });
    }
  }

  void _onCameraMove(CameraPosition position) {
    _cameraCenter = position.target;
  }

  /// The camera has settled: search around it, unless the app moved it itself
  /// (the location flow already searches there).
  void _onCameraIdle() {
    if (_programmaticMove) {
      _programmaticMove = false;
      return;
    }
    _panDebounce?.cancel();
    _panDebounce = Timer(
      const Duration(milliseconds: 300),
      () => _fetchGyms(_cameraCenter),
    );
  }

  Future<void> _ensureDetails(Gym gym, {int delayMs = 0}) async {
    if (_detailsCache.containsKey(gym.placeId) ||
        _detailsLoading.contains(gym.placeId))
      return;
    _detailsLoading.add(gym.placeId);
    if (delayMs > 0) await Future.delayed(Duration(milliseconds: delayMs));
    if (!mounted) return;
    try {
      final details = await _gymAgentApi.getDetails(gym);
      if (!mounted) return;
      setState(() {
        _detailsCache[gym.placeId] = details;
        _detailsFailed.remove(gym.placeId);
      });
    } catch (_) {
      // The gym-agent enrichment service is unreachable/unavailable - stop
      // showing a loading skeleton that would otherwise shimmer forever.
      if (mounted) setState(() => _detailsFailed.add(gym.placeId));
    } finally {
      _detailsLoading.remove(gym.placeId);
    }
  }

  Future<void> _openDirections(Gym gym) async {
    final uri = Uri.parse(
      'https://www.google.com/maps/dir/?api=1&destination=${gym.lat},${gym.lng}',
    );
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  Future<void> _showWorkoutSuggestions(Gym gym) async {
    await _ensureDetails(gym);
    if (!mounted) return;
    final details =
        _detailsCache[gym.placeId] ??
        const GymDetails(
          placeId: '',
          source: 'ai-generic',
          equipment: [],
          classes: [],
        );

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
          final result = await _gymAgentApi.getWorkoutSuggestions(
            details,
            gym.name,
          );
          _workoutCache[gym.placeId] = result;
          return result;
        },
      ),
    );
  }

  void _showGymSheet(Gym gym) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => StatefulBuilder(
        builder: (context, setSheetState) {
          // _ensureDetails updates the parent screen's state, not this
          // sheet's - so explicitly refresh the sheet once it resolves.
          // Safe to call every rebuild: _ensureDetails no-ops if a fetch
          // for this gym is already cached, failed, or in flight.
          if (!_detailsCache.containsKey(gym.placeId) &&
              !_detailsFailed.contains(gym.placeId)) {
            _ensureDetails(gym).then((_) {
              if (context.mounted) setSheetState(() {});
            });
          }
          return _GymDetailSheet(
            gym: gym,
            details: _detailsCache[gym.placeId],
            detailsFailed: _detailsFailed.contains(gym.placeId),
            onDirections: () => _openDirections(gym),
            onFindWorkouts: () => _showWorkoutSuggestions(gym),
          );
        },
      ),
    );
  }

  List<Gym> get _filteredGyms {
    final query = _searchQuery.trim().toLowerCase();
    if (query.isEmpty) return _gyms;
    return _gyms.where((gym) {
      return gym.name.toLowerCase().contains(query) ||
          (gym.address?.toLowerCase().contains(query) ?? false);
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _filteredGyms;
    final visible = filtered.take(_visibleCount).toList();
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
          physics: const AlwaysScrollableScrollPhysics(
            parent: BouncingScrollPhysics(),
          ),
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 100),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const OutlineText(text: "FIND YOUR", fontSize: 24),
                  Text(
                    "NEAREST GYM",
                    style: GoogleFonts.oswald(
                      fontSize: 32,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 1.5,
                      color: AppColors.accent,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    "Discover fitness centres near you, with AI-suggested workouts for each one.",
                    style: GoogleFonts.inter(
                      fontSize: 13,
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
              ).animate().fadeIn(duration: 300.ms).slideY(begin: 0.08, end: 0),
              const SizedBox(height: 16),
              _GymSearchBar(
                controller: _searchController,
                onChanged: (value) => setState(() => _searchQuery = value),
              ).animate(delay: 60.ms).fadeIn(duration: 300.ms).slideY(
                begin: 0.08,
                end: 0,
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Icon(
                    _locating
                        ? Icons.my_location
                        : (_usingFallback
                              ? Icons.location_disabled
                              : Icons.location_on),
                    size: 14,
                    color: (_usingFallback && _locationIssue != null)
                        ? AppColors.error
                        : AppColors.accent,
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      (!_locating && _usingFallback && _locationIssue != null)
                          ? _locationIssue!
                          : statusText,
                      style: GoogleFonts.inter(
                        fontSize: 12,
                        color: (_usingFallback && _locationIssue != null)
                            ? AppColors.error
                            : AppColors.textSecondary,
                      ),
                    ),
                  ),
                  if (_locating || _searching)
                    const SizedBox(
                      width: 12,
                      height: 12,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor: AlwaysStoppedAnimation(AppColors.accent),
                      ),
                    ),
                ],
              ),
              if (!_locating && _usingFallback && _locationIssue != null) ...[
                const SizedBox(height: 8),
                Align(
                  alignment: Alignment.centerLeft,
                  child: SlantedButton(
                    text: _locationPermissionBlocked
                        ? "OPEN SETTINGS"
                        : "RETRY",
                    isSecondary: true,
                    paddingVertical: 8,
                    paddingHorizontal: 18,
                    onPressed: _locationPermissionBlocked
                        ? () => Geolocator.openAppSettings()
                        : _locateAndSearch,
                  ),
                ),
              ],
              const SizedBox(height: 12),
              _buildMap(),
              const SizedBox(height: 10),
              _buildLegend(),
              const SizedBox(height: 24),
              Text(
                "GYM LIST",
                style: GoogleFonts.oswald(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 1.0,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 12),
              _buildList(visible, filtered.length),
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
        boxShadow: const [
          BoxShadow(
            color: AppColors.shadowAccent,
            blurRadius: 16,
            spreadRadius: 1,
          ),
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: Stack(
        children: [
          GoogleMap(
            initialCameraPosition: const CameraPosition(
              target: _fallbackCenter,
              zoom: 12,
            ),
            style: _darkMapStyle,
            onMapCreated: (controller) {
              _mapController = controller;
              _mapReady = true;
              if (_userLocation != null) {
                _animateCameraTo(_userLocation!, 13);
              }
            },
            onCameraMove: _onCameraMove,
            onCameraIdle: _onCameraIdle,
            markers: {
              if (_userLocation != null)
                Marker(
                  markerId: const MarkerId('me'),
                  position: _userLocation!,
                  icon: _userIcon ?? BitmapDescriptor.defaultMarker,
                  anchor: const Offset(0.5, 0.5),
                  zIndexInt: 2,
                ),
              for (final gym in _gyms)
                Marker(
                  markerId: MarkerId(gym.placeId),
                  position: LatLng(gym.lat, gym.lng),
                  icon: _gymIcon ?? BitmapDescriptor.defaultMarker,
                  anchor: const Offset(0.5, 1.0),
                  onTap: () => _showGymSheet(gym),
                ),
            },
            zoomControlsEnabled: false,
            myLocationButtonEnabled: false,
            mapToolbarEnabled: false,
            compassEnabled: false,
            // The map sits inside a scrolling page: let it claim drags.
            gestureRecognizers: {
              Factory<OneSequenceGestureRecognizer>(
                () => EagerGestureRecognizer(),
              ),
            },
          ),
          IgnorePointer(
            child: AnimatedOpacity(
              duration: const Duration(milliseconds: 300),
              opacity: _locating ? 1 : 0,
              child: Container(
                color: AppColors.bgPrimary.withOpacity(0.65),
                alignment: Alignment.center,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const SizedBox(
                      width: 22,
                      height: 22,
                      child: CircularProgressIndicator(
                        strokeWidth: 2.4,
                        valueColor: AlwaysStoppedAnimation(AppColors.accent),
                      ),
                    ),
                    const SizedBox(height: 10),
                    Text(
                      "Locating you…",
                      style: GoogleFonts.inter(
                        fontSize: 12,
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLegend() {
    return Row(
      children: [
        Container(
          width: 10,
          height: 10,
          decoration: const BoxDecoration(
            color: AppColors.info,
            shape: BoxShape.circle,
          ),
        ),
        const SizedBox(width: 6),
        Text(
          "Your location",
          style: GoogleFonts.inter(fontSize: 11, color: AppColors.textMuted),
        ),
        const SizedBox(width: 16),
        const Icon(Icons.fitness_center, size: 12, color: AppColors.accent),
        const SizedBox(width: 6),
        Text(
          "Gym • tap for details",
          style: GoogleFonts.inter(fontSize: 11, color: AppColors.textMuted),
        ),
      ],
    );
  }

  Widget _buildList(List<Gym> visible, int filteredCount) {
    if ((_locating || _searching) && _gyms.isEmpty) {
      return Column(
        children: List.generate(
          3,
          (i) => const Padding(
            padding: EdgeInsets.only(bottom: 14),
            child: SkeletonBox(height: 130, borderRadius: 14),
          ),
        ),
      );
    }
    if (_searchError != null && _gyms.isEmpty) {
      return _emptyCard(
        Icons.wifi_off,
        _searchError!,
        retryLabel: "RETRY",
        onRetry: () => _fetchGyms(_userLocation ?? _fallbackCenter),
      );
    }
    if (_gyms.isEmpty) {
      return _emptyCard(Icons.location_off, "No gyms found nearby.");
    }
    if (filteredCount == 0) {
      return _emptyCard(
        Icons.search_off,
        'No gyms match "$_searchQuery".',
        retryLabel: "CLEAR SEARCH",
        onRetry: () {
          _searchController.clear();
          setState(() => _searchQuery = '');
        },
      );
    }

    return Column(
      children: [
        ...List.generate(visible.length, (index) {
          final gym = visible[index];
          return Padding(
            padding: const EdgeInsets.only(bottom: 14),
            child:
                _GymCard(
                      gym: gym,
                      details: _detailsCache[gym.placeId],
                      detailsFailed: _detailsFailed.contains(gym.placeId),
                      onVisible: () =>
                          _ensureDetails(gym, delayMs: index * 600),
                      onDirections: () => _openDirections(gym),
                      onFindWorkouts: () => _showWorkoutSuggestions(gym),
                      onTap: () => _showGymSheet(gym),
                    )
                    .animate(delay: (index * 60).ms)
                    .fadeIn(duration: 300.ms)
                    .slideY(begin: 0.08, end: 0, curve: Curves.easeOut),
          );
        }),
        if (_visibleCount < filteredCount)
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

  Widget _emptyCard(
    IconData icon,
    String message, {
    String? retryLabel,
    VoidCallback? onRetry,
  }) {
    return Container(
          padding: const EdgeInsets.all(40),
          width: double.infinity,
          decoration: BoxDecoration(
            color: AppColors.bgCard,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Column(
            children: [
              Icon(icon, size: 40, color: AppColors.textMuted),
              const SizedBox(height: 12),
              Text(
                message,
                style: GoogleFonts.inter(color: AppColors.textSecondary),
                textAlign: TextAlign.center,
              ),
              if (onRetry != null) ...[
                const SizedBox(height: 16),
                SlantedButton(
                  text: retryLabel ?? "RETRY",
                  isSecondary: true,
                  paddingVertical: 10,
                  paddingHorizontal: 22,
                  onPressed: onRetry,
                ),
              ],
            ],
          ),
        )
        .animate()
        .fadeIn(duration: 300.ms)
        .slideY(begin: 0.08, end: 0, curve: Curves.easeOut);
  }
}

/// A location/gym-name filter for the already-loaded gym list, styled to
/// match the rest of the screen's liquid-glass surfaces.
class _GymSearchBar extends StatefulWidget {
  final TextEditingController controller;
  final ValueChanged<String> onChanged;

  const _GymSearchBar({required this.controller, required this.onChanged});

  @override
  State<_GymSearchBar> createState() => _GymSearchBarState();
}

class _GymSearchBarState extends State<_GymSearchBar> {
  bool _focused = false;

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: _focused ? AppColors.accent : AppColors.border,
          width: _focused ? 1.4 : 1,
        ),
        boxShadow: _focused
            ? const [
                BoxShadow(
                  color: AppColors.shadowAccent,
                  blurRadius: 12,
                  spreadRadius: 1,
                ),
              ]
            : const [],
      ),
      child: Focus(
        onFocusChange: (focused) => setState(() => _focused = focused),
        child: Row(
          children: [
            const SizedBox(width: 14),
            Icon(
              Icons.location_on_outlined,
              size: 18,
              color: _focused ? AppColors.accent : AppColors.textMuted,
            ),
            const SizedBox(width: 8),
            Expanded(
              child: TextField(
                controller: widget.controller,
                onChanged: widget.onChanged,
                style: GoogleFonts.inter(
                  fontSize: 13,
                  color: AppColors.textPrimary,
                ),
                cursorColor: AppColors.accent,
                decoration: InputDecoration(
                  isDense: true,
                  border: InputBorder.none,
                  filled: false,
                  hintText: "Search by gym name or area…",
                  hintStyle: GoogleFonts.inter(
                    fontSize: 13,
                    color: AppColors.textMuted,
                  ),
                  contentPadding: const EdgeInsets.symmetric(vertical: 14),
                ),
              ),
            ),
            AnimatedOpacity(
              duration: const Duration(milliseconds: 150),
              opacity: widget.controller.text.isEmpty ? 0 : 1,
              child: IgnorePointer(
                ignoring: widget.controller.text.isEmpty,
                child: IconButton(
                  icon: const Icon(
                    Icons.close_rounded,
                    size: 18,
                    color: AppColors.textMuted,
                  ),
                  onPressed: () {
                    widget.controller.clear();
                    widget.onChanged('');
                  },
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _GymCard extends StatefulWidget {
  final Gym gym;
  final GymDetails? details;
  final bool detailsFailed;
  final VoidCallback onVisible;
  final VoidCallback onDirections;
  final VoidCallback onFindWorkouts;
  final VoidCallback onTap;

  const _GymCard({
    required this.gym,
    required this.details,
    this.detailsFailed = false,
    required this.onVisible,
    required this.onDirections,
    required this.onFindWorkouts,
    required this.onTap,
  });

  @override
  State<_GymCard> createState() => _GymCardState();
}

class _GymCardState extends State<_GymCard> {
  bool _isPressed = false;

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
      onTapDown: (_) => setState(() => _isPressed = true),
      onTapUp: (_) => setState(() => _isPressed = false),
      onTapCancel: () => setState(() => _isPressed = false),
      child: AnimatedScale(
        scale: _isPressed ? 0.97 : 1.0,
        duration: const Duration(milliseconds: 120),
        curve: Curves.easeOut,
        child: LiquidGlassContainer(
        padding: const EdgeInsets.all(16),
        borderRadius: BorderRadius.circular(14),
        blur: false,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    gym.name,
                    style: GoogleFonts.oswald(
                      fontSize: 17,
                      fontWeight: FontWeight.bold,
                      color: AppColors.textPrimary,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                if (gym.distanceMeters != null) ...[
                  const SizedBox(width: 8),
                  BadgeChip(
                    label: "${gym.distanceKm.toStringAsFixed(1)} KM",
                    isAccent: true,
                  ),
                ],
              ],
            ),
            if (gym.address != null) ...[
              const SizedBox(height: 4),
              Text(
                gym.address!,
                style: GoogleFonts.inter(
                  fontSize: 12,
                  color: AppColors.textSecondary,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],
            const SizedBox(height: 10),
            if (details == null && !widget.detailsFailed)
              const SkeletonBox(height: 22, borderRadius: 6)
            else if (details != null &&
                (details.equipment.isNotEmpty || details.classes.isNotEmpty))
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: [
                  ...details.equipment
                      .take(4)
                      .map((e) => BadgeChip(label: e, isAccent: false)),
                  ...details.classes
                      .take(2)
                      .map((e) => BadgeChip(label: e, isAccent: false)),
                ],
              ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: widget.onDirections,
                    style: OutlinedButton.styleFrom(
                      side: const BorderSide(color: AppColors.border),
                      padding: const EdgeInsets.symmetric(vertical: 10),
                    ),
                    icon: const Icon(
                      Icons.directions,
                      size: 16,
                      color: AppColors.accent,
                    ),
                    label: Text(
                      "DIRECTIONS",
                      style: GoogleFonts.oswald(
                        fontSize: 12,
                        color: AppColors.textPrimary,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
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
                    icon: const Icon(
                      Icons.auto_awesome,
                      size: 16,
                      color: AppColors.bgPrimary,
                    ),
                    label: Text(
                      "WORKOUTS",
                      style: GoogleFonts.oswald(
                        fontSize: 12,
                        color: AppColors.bgPrimary,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
        ),
      ),
    );
  }
}

class _GymDetailSheet extends StatelessWidget {
  final Gym gym;
  final GymDetails? details;
  final bool detailsFailed;
  final VoidCallback onDirections;
  final VoidCallback onFindWorkouts;

  const _GymDetailSheet({
    required this.gym,
    required this.details,
    this.detailsFailed = false,
    required this.onDirections,
    required this.onFindWorkouts,
  });

  Future<void> _launch(String scheme, String value) async {
    await launchUrl(Uri.parse('$scheme:$value'));
  }

  Future<void> _launchWebsite(String url) async {
    final normalized = url.startsWith('http') ? url : 'https://$url';
    await launchUrl(
      Uri.parse(normalized),
      mode: LaunchMode.externalApplication,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
      ),
      child: LiquidGlassContainer(
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        tint: AppColors.bgPrimary,
        tintOpacity: 0.75,
        blur: false,
        border: const Border(
          top: BorderSide(color: AppColors.accent, width: 2),
        ),
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
                  decoration: BoxDecoration(
                    color: AppColors.textMuted,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              Text(
                gym.name,
                style: GoogleFonts.oswald(
                  fontSize: 22,
                  fontWeight: FontWeight.bold,
                  color: AppColors.accent,
                ),
              ),
              if (gym.distanceMeters != null) ...[
                const SizedBox(height: 4),
                Text(
                  "${gym.distanceKm.toStringAsFixed(1)} km away",
                  style: GoogleFonts.inter(
                    fontSize: 12,
                    color: AppColors.textMuted,
                  ),
                ),
              ],
              if (gym.address != null) ...[
                const SizedBox(height: 10),
                Text(
                  gym.address!,
                  style: GoogleFonts.inter(
                    fontSize: 13,
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
              const SizedBox(height: 16),
              if (details == null && detailsFailed)
                Text(
                  "Couldn't load extra details for this gym.",
                  style: GoogleFonts.inter(
                    fontSize: 12,
                    color: AppColors.textMuted,
                    fontStyle: FontStyle.italic,
                  ),
                )
              else if (details == null)
                const SkeletonBox(height: 60, borderRadius: 10)
              else ...[
                if (details!.equipment.isNotEmpty) ...[
                  Text(
                    "EQUIPMENT",
                    style: GoogleFonts.oswald(
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                      color: AppColors.textPrimary,
                      letterSpacing: 1.0,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: details!.equipment
                        .map((e) => BadgeChip(label: e, isAccent: false))
                        .toList(),
                  ),
                  const SizedBox(height: 12),
                ],
                if (details!.classes.isNotEmpty) ...[
                  Text(
                    "CLASSES",
                    style: GoogleFonts.oswald(
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                      color: AppColors.textPrimary,
                      letterSpacing: 1.0,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: details!.classes
                        .map((e) => BadgeChip(label: e, isAccent: true))
                        .toList(),
                  ),
                  const SizedBox(height: 12),
                ],
                if (details!.openingHours != null)
                  _infoRow(Icons.schedule, details!.openingHours!),
                if (details!.phone != null)
                  GestureDetector(
                    onTap: () => _launch('tel', details!.phone!),
                    child: _infoRow(Icons.call, details!.phone!, accent: true),
                  ),
                if (details!.email != null)
                  GestureDetector(
                    onTap: () => _launch('mailto', details!.email!),
                    child: _infoRow(
                      Icons.email_outlined,
                      details!.email!,
                      accent: true,
                    ),
                  ),
                if (gym.website != null)
                  GestureDetector(
                    onTap: () => _launchWebsite(gym.website!),
                    child: _infoRow(Icons.language, gym.website!, accent: true),
                  ),
              ],
              const SizedBox(height: 20),
              Row(
                children: [
                  Expanded(
                    child: SlantedButton(
                      text: "DIRECTIONS",
                      icon: Icons.directions,
                      isSecondary: true,
                      onPressed: onDirections,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: SlantedButton(
                      text: "WORKOUTS",
                      icon: Icons.auto_awesome,
                      onPressed: onFindWorkouts,
                    ),
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
          Icon(
            icon,
            size: 16,
            color: accent ? AppColors.accent : AppColors.textMuted,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              text,
              style: GoogleFonts.inter(
                fontSize: 13,
                color: accent ? AppColors.accent : AppColors.textSecondary,
              ),
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

  const _WorkoutSuggestionsSheet({
    required this.gym,
    required this.details,
    required this.cached,
    required this.onLoad,
  });

  @override
  State<_WorkoutSuggestionsSheet> createState() =>
      _WorkoutSuggestionsSheetState();
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
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
      ),
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxHeight: MediaQuery.of(context).size.height * 0.85,
        ),
        child: LiquidGlassContainer(
          borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
          tint: AppColors.bgPrimary,
          tintOpacity: 0.75,
          blur: false,
          border: const Border(
            top: BorderSide(color: AppColors.accent, width: 2),
          ),
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
                    decoration: BoxDecoration(
                      color: AppColors.textMuted,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ),
                Row(
                  children: [
                    const Icon(
                      Icons.auto_awesome,
                      color: AppColors.accent,
                      size: 20,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        "AI WORKOUTS · ${widget.gym.name}",
                        style: GoogleFonts.oswald(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          color: AppColors.accent,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                if (_loading)
                  Column(
                    children: List.generate(
                      2,
                      (i) => const Padding(
                        padding: EdgeInsets.only(bottom: 12),
                        child: SkeletonBox(height: 100, borderRadius: 12),
                      ),
                    ),
                  )
                else if (_error != null)
                  Text(
                    _error!,
                    style: GoogleFonts.inter(color: AppColors.error),
                  )
                else if (_result != null) ...[
                  ..._result!.workouts.map((w) => _WorkoutCard(workout: w)),
                  if (_result!.notes != null) ...[
                    const SizedBox(height: 4),
                    Text(
                      _result!.notes!,
                      style: GoogleFonts.inter(
                        fontSize: 11,
                        color: AppColors.textMuted,
                        fontStyle: FontStyle.italic,
                      ),
                    ),
                  ],
                ],
                const SizedBox(height: 8),
              ],
            ),
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
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  workout.name,
                  style: GoogleFonts.oswald(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: AppColors.textPrimary,
                  ),
                ),
              ),
              Text(
                "${workout.durationMinutes} MIN",
                style: GoogleFonts.inter(
                  fontSize: 11,
                  color: AppColors.textMuted,
                  fontWeight: FontWeight.bold,
                ),
              ),
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
            Text(
              workout.description,
              style: GoogleFonts.inter(
                fontSize: 12.5,
                color: AppColors.textSecondary,
              ),
            ),
          ],
          if (workout.equipmentUsed.isNotEmpty) ...[
            const SizedBox(height: 8),
            Wrap(
              spacing: 4,
              runSpacing: 4,
              children: workout.equipmentUsed
                  .map(
                    (e) => Text(
                      "• $e",
                      style: GoogleFonts.inter(
                        fontSize: 11,
                        color: AppColors.textMuted,
                      ),
                    ),
                  )
                  .toList(),
            ),
          ],
        ],
      ),
    );
  }
}

/// Dark Google map style matching the app (and the website's dark map).
const String _darkMapStyle = '''
[
  {"elementType": "geometry", "stylers": [{"color": "#1a1a1a"}]},
  {"elementType": "labels.text.fill", "stylers": [{"color": "#8a8a8a"}]},
  {"elementType": "labels.text.stroke", "stylers": [{"color": "#111111"}]},
  {"featureType": "poi", "stylers": [{"visibility": "off"}]},
  {"featureType": "transit", "stylers": [{"visibility": "off"}]},
  {"featureType": "road", "elementType": "geometry", "stylers": [{"color": "#2b2b2b"}]},
  {"featureType": "road.highway", "elementType": "geometry", "stylers": [{"color": "#3a3a3a"}]},
  {"featureType": "water", "elementType": "geometry", "stylers": [{"color": "#0b1620"}]},
  {"featureType": "administrative", "elementType": "geometry.stroke", "stylers": [{"color": "#333333"}]}
]
''';
