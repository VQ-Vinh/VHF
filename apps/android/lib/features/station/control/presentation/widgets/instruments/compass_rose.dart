import 'dart:math' as math;

import 'package:flutter/material.dart';

/// Heading on a fixed compass card with a turning needle.
///
/// The card stays put and the needle moves, which is how a reader finds north
/// at a glance. A bounded graphic, so it holds its size at every text scale.
class CompassRose extends StatelessWidget {
  const CompassRose({super.key, required this.degrees, this.size = 92});
  final double? degrees;
  final double size;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return SizedBox(
      key: const ValueKey('compass-rose'),
      width: size,
      height: size,
      child: CustomPaint(
        painter: _CompassPainter(
          degrees: degrees,
          face: colors.surfaceContainerHighest.withValues(alpha: 0.45),
          ring: colors.outlineVariant,
          tick: colors.onSurfaceVariant.withValues(alpha: 0.55),
          cardinal: colors.onSurfaceVariant,
          needle: colors.primary,
          tail: colors.onSurfaceVariant.withValues(alpha: 0.35),
          textDirection: Directionality.of(context),
        ),
      ),
    );
  }
}

class _CompassPainter extends CustomPainter {
  _CompassPainter({
    required this.degrees,
    required this.face,
    required this.ring,
    required this.tick,
    required this.cardinal,
    required this.needle,
    required this.tail,
    required this.textDirection,
  });
  final double? degrees;
  final Color face, ring, tick, cardinal, needle, tail;
  final TextDirection textDirection;

  @override
  void paint(Canvas canvas, Size size) {
    final centre = Offset(size.width / 2, size.height / 2);
    final radius = math.min(size.width, size.height) / 2 - 1;
    if (radius <= 0) return;

    canvas.drawCircle(centre, radius, Paint()..color = face);
    canvas.drawCircle(
      centre,
      radius,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1
        ..color = ring,
    );

    // Ticks every 15 degrees; the eight principal points read longer.
    for (var angle = 0; angle < 360; angle += 15) {
      final principal = angle % 45 == 0;
      final length = principal ? radius * 0.16 : radius * 0.09;
      final radians = angle * math.pi / 180;
      final direction = Offset(math.sin(radians), -math.cos(radians));
      canvas.drawLine(
        centre + direction * (radius - length),
        centre + direction * (radius - 2),
        Paint()
          ..strokeWidth = principal ? 1.6 : 1
          ..color = tick,
      );
    }

    for (final entry in const {0: 'N', 90: 'E', 180: 'S', 270: 'W'}.entries) {
      final radians = entry.key * math.pi / 180;
      final direction = Offset(math.sin(radians), -math.cos(radians));
      final painter = TextPainter(
        text: TextSpan(
          text: entry.value,
          style: TextStyle(
            fontSize: radius * 0.24,
            height: 1,
            fontWeight: FontWeight.w700,
            color: cardinal,
          ),
        ),
        textDirection: textDirection,
      )..layout();
      final at = centre + direction * (radius * 0.68);
      painter.paint(
        canvas,
        Offset(at.dx - painter.width / 2, at.dy - painter.height / 2),
      );
    }

    if (degrees == null) return;

    canvas.save();
    canvas.translate(centre.dx, centre.dy);
    canvas.rotate(degrees! * math.pi / 180);
    final reach = radius * 0.58;
    final head =
        Path()
          ..moveTo(0, -reach)
          ..lineTo(radius * 0.09, 0)
          ..lineTo(-radius * 0.09, 0)
          ..close();
    canvas.drawPath(head, Paint()..color = needle);
    final back =
        Path()
          ..moveTo(0, reach * 0.62)
          ..lineTo(radius * 0.07, 0)
          ..lineTo(-radius * 0.07, 0)
          ..close();
    canvas.drawPath(back, Paint()..color = tail);
    canvas.restore();

    canvas.drawCircle(centre, radius * 0.06, Paint()..color = needle);
  }

  @override
  bool shouldRepaint(_CompassPainter old) =>
      old.degrees != degrees ||
      old.face != face ||
      old.ring != ring ||
      old.tick != tick ||
      old.cardinal != cardinal ||
      old.needle != needle ||
      old.tail != tail ||
      old.textDirection != textDirection;
}
