import 'dart:math' as math;

import 'package:flutter/material.dart';

/// Sounder-style depth scale over 0-10000 m.
///
/// The axis is logarithmic on purpose. Laid out linearly, a coastal 8 m
/// reading would sit 0.08% along a 10 km track and be invisible; decades are
/// how a sounder presents the same range. Anything under a metre pins to the
/// left edge, since a log axis has no zero.
class DepthScale extends StatelessWidget {
  const DepthScale({
    super.key,
    required this.metres,
    this.height = 30,
    this.labelled = true,
  });
  final double? metres;
  final double height;

  /// Decade labels under the track. Off in a strip cell, where the track is
  /// a few pixels tall and the numbers would have nowhere to sit.
  final bool labelled;

  static const double minMetres = 1;
  static const double maxMetres = 10000;

  /// Position of [metres] along the track, 0 at 1 m and 1 at 10 km.
  static double fraction(double metres) =>
      (math.log(metres.clamp(minMetres, maxMetres)) / math.ln10) /
      (math.log(maxMetres) / math.ln10);

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return SizedBox(
      height: height,
      width: double.infinity,
      child: CustomPaint(
        painter: _DepthScalePainter(
          metres: metres,
          labelled: labelled,
          track: colors.surfaceContainerHighest,
          fill: colors.primary,
          tick: colors.outlineVariant,
          label: colors.onSurfaceVariant,
          textDirection: Directionality.of(context),
        ),
      ),
    );
  }
}

class _DepthScalePainter extends CustomPainter {
  _DepthScalePainter({
    required this.metres,
    required this.labelled,
    required this.track,
    required this.fill,
    required this.tick,
    required this.label,
    required this.textDirection,
  });
  final double? metres;
  final bool labelled;
  final Color track, fill, tick, label;
  final TextDirection textDirection;

  // Metres and the label drawn under that tick. A list, not a map: Dart will
  // not accept doubles as constant map keys.
  static const _decades = <(double, String)>[
    (1, '1'),
    (10, '10'),
    (100, '100'),
    (1000, '1k'),
    (10000, '10k'),
  ];

  @override
  void paint(Canvas canvas, Size size) {
    if (size.width <= 0) return;
    const trackHeight = 8.0;
    final radius = const Radius.circular(4);
    final trackRect = Rect.fromLTWH(0, 0, size.width, trackHeight);
    canvas.drawRRect(
      RRect.fromRectAndRadius(trackRect, radius),
      Paint()..color = track,
    );

    if (metres != null) {
      final t = DepthScale.fraction(metres!);
      final filled = (size.width * t).clamp(trackHeight, size.width);
      canvas.drawRRect(
        RRect.fromRectAndRadius(
          Rect.fromLTWH(0, 0, filled, trackHeight),
          radius,
        ),
        Paint()..color = fill,
      );
    }

    if (!labelled) return;

    // Decade ticks and their labels, skipping any label that would collide
    // with the previous one on a narrow card.
    var occupied = double.negativeInfinity;
    for (final (metres, text) in _decades) {
      final x = size.width * DepthScale.fraction(metres);
      canvas.drawRect(
        Rect.fromLTWH(x.clamp(0, size.width - 1), trackHeight + 3, 1, 4),
        Paint()..color = tick,
      );

      final painter = TextPainter(
        text: TextSpan(
          text: text,
          style: TextStyle(fontSize: 9, height: 1, color: label),
        ),
        textDirection: textDirection,
      )..layout();
      final left = (x - painter.width / 2).clamp(
        0.0,
        size.width - painter.width,
      );
      if (left <= occupied + 4) continue;
      occupied = left + painter.width;
      painter.paint(canvas, Offset(left, trackHeight + 9));
    }
  }

  @override
  bool shouldRepaint(_DepthScalePainter old) =>
      old.metres != metres ||
      old.labelled != labelled ||
      old.track != track ||
      old.fill != fill ||
      old.tick != tick ||
      old.label != label ||
      old.textDirection != textDirection;
}
