import 'dart:ui';

import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class _OrbSpec {
  final Alignment begin;
  final Alignment end;
  final double size;
  final Color color;
  final double parallax;

  const _OrbSpec({
    required this.begin,
    required this.end,
    required this.size,
    required this.color,
    required this.parallax,
  });
}

/// A slow-drifting ambient glow backdrop with subtle scroll-linked parallax.
/// Purely decorative — sits behind scrollable content and never intercepts touches.
class AmbientGlowBackground extends StatefulWidget {
  final ScrollController scrollController;

  const AmbientGlowBackground({super.key, required this.scrollController});

  @override
  State<AmbientGlowBackground> createState() => _AmbientGlowBackgroundState();
}

class _AmbientGlowBackgroundState extends State<AmbientGlowBackground> with TickerProviderStateMixin {
  late final List<AnimationController> _controllers;
  late final List<Animation<Alignment>> _alignments;
  double _scrollOffset = 0;

  static const List<_OrbSpec> _orbs = [
    _OrbSpec(
      begin: Alignment(-1.1, -0.9),
      end: Alignment(-0.5, -0.5),
      size: 300,
      color: AppColors.accent,
      parallax: 0.06,
    ),
    _OrbSpec(
      begin: Alignment(1.2, -0.2),
      end: Alignment(0.7, 0.3),
      size: 260,
      color: AppColors.info,
      parallax: -0.09,
    ),
    _OrbSpec(
      begin: Alignment(-0.8, 1.1),
      end: Alignment(-0.2, 0.6),
      size: 280,
      color: AppColors.accent,
      parallax: 0.04,
    ),
  ];

  @override
  void initState() {
    super.initState();
    _controllers = List.generate(_orbs.length, (i) {
      final controller = AnimationController(
        vsync: this,
        duration: Duration(seconds: 20 + i * 4),
      )..repeat(reverse: true);
      return controller;
    });
    _alignments = List.generate(
      _orbs.length,
      (i) => AlignmentTween(begin: _orbs[i].begin, end: _orbs[i].end).animate(
        CurvedAnimation(parent: _controllers[i], curve: Curves.easeInOut),
      ),
    );
    widget.scrollController.addListener(_onScroll);
  }

  void _onScroll() {
    if (!widget.scrollController.hasClients) return;
    setState(() => _scrollOffset = widget.scrollController.offset);
  }

  @override
  void dispose() {
    widget.scrollController.removeListener(_onScroll);
    for (final c in _controllers) {
      c.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: RepaintBoundary(
        child: Container(
          color: AppColors.bgPrimary,
          child: Stack(
            children: List.generate(_orbs.length, (i) {
              final spec = _orbs[i];
              final parallaxShift = (_scrollOffset * spec.parallax).clamp(-45.0, 45.0);
              return AnimatedBuilder(
                animation: _controllers[i],
                builder: (context, child) {
                  return Align(
                    alignment: _alignments[i].value,
                    child: Transform.translate(
                      offset: Offset(0, -parallaxShift),
                      child: child,
                    ),
                  );
                },
                child: ImageFiltered(
                  imageFilter: ImageFilter.blur(sigmaX: 55, sigmaY: 55),
                  child: Container(
                    width: spec.size,
                    height: spec.size,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: RadialGradient(
                        colors: [
                          spec.color.withOpacity(0.22),
                          spec.color.withOpacity(0.0),
                        ],
                      ),
                    ),
                  ),
                ),
              );
            }),
          ),
        ),
      ),
    );
  }
}
