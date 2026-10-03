import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';

import '../theme/app_theme.dart';

/// Google Maps markers are bitmaps, so the app's gym pin and "you are here"
/// dot are drawn once with a canvas and cached by the screen.
class MapMarkerIcons {
  static const double _gymWidth = 36;
  static const double _gymHeight = 44;
  static const double _userSize = 28;

  /// The accent circle with a dumbbell and a small tail, anchored at its tip.
  static Future<BitmapDescriptor> gymPin({required double pixelRatio}) {
    return _render(
      width: _gymWidth,
      height: _gymHeight,
      pixelRatio: pixelRatio,
      paint: (canvas) {
        const cx = _gymWidth / 2;
        const cy = 18.0;

        canvas.drawCircle(
          const Offset(cx, cy + 1),
          16,
          Paint()
            ..color = AppColors.shadowAccent
            ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4),
        );
        canvas.drawCircle(
          const Offset(cx, cy),
          15,
          Paint()
            ..shader = const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [AppColors.accent, AppColors.accentDark],
            ).createShader(Rect.fromCircle(center: const Offset(cx, cy), radius: 15)),
        );

        final tail = Path()
          ..moveTo(cx - 5, cy + 12)
          ..lineTo(cx + 5, cy + 12)
          ..lineTo(cx, _gymHeight - 2)
          ..close();
        canvas.drawPath(tail, Paint()..color = AppColors.accentDark);

        final icon = Icons.fitness_center;
        final painter = TextPainter(
          text: TextSpan(
            text: String.fromCharCode(icon.codePoint),
            style: TextStyle(
              fontSize: 17,
              fontFamily: icon.fontFamily,
              package: icon.fontPackage,
              color: AppColors.bgPrimary,
            ),
          ),
          textDirection: TextDirection.ltr,
        )..layout();
        painter.paint(
          canvas,
          Offset(cx - painter.width / 2, cy - painter.height / 2),
        );
      },
    );
  }

  /// A blue dot with a white ring.
  static Future<BitmapDescriptor> userDot({required double pixelRatio}) {
    return _render(
      width: _userSize,
      height: _userSize,
      pixelRatio: pixelRatio,
      paint: (canvas) {
        const c = Offset(_userSize / 2, _userSize / 2);
        canvas.drawCircle(
          c,
          13,
          Paint()..color = AppColors.info.withValues(alpha: 0.28),
        );
        canvas.drawCircle(c, 8, Paint()..color = Colors.white);
        canvas.drawCircle(c, 6, Paint()..color = AppColors.info);
      },
    );
  }

  static Future<BitmapDescriptor> _render({
    required double width,
    required double height,
    required double pixelRatio,
    required void Function(Canvas canvas) paint,
  }) async {
    final recorder = ui.PictureRecorder();
    final canvas = Canvas(recorder)..scale(pixelRatio);
    paint(canvas);
    final image = await recorder.endRecording().toImage(
      (width * pixelRatio).ceil(),
      (height * pixelRatio).ceil(),
    );
    final data = await image.toByteData(format: ui.ImageByteFormat.png);
    return BitmapDescriptor.bytes(
      data!.buffer.asUint8List(),
      imagePixelRatio: pixelRatio,
    );
  }
}
