import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/material.dart';

/// Heading on a fixed compass card with a turning needle.
///
/// The card stays put and the needle moves, which is how a reader finds north
/// at a glance. A bounded graphic, so it holds its size at every text scale.
class CompassRose extends StatelessWidget {
  const CompassRose({super.key, required this.degrees, this.size = 92});
  final double? degrees;
  final double size;

  /// North is red on any compass. Kept apart from the theme's error colour,
  /// which means something has gone wrong; the same values as the desktop's
  /// `compass_north` token.
  static Color north(Brightness brightness) =>
      brightness == Brightness.dark
          ? const Color(0xFFF0616B)
          : const Color(0xFFC62F3A);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    return SizedBox(
      key: const ValueKey('compass-rose'),
      width: size,
      height: size,
      child: CustomPaint(
        painter: _CompassPainter(
          degrees: degrees,
          surface: colors.surface,
          sunken: colors.surfaceContainerHighest,
          ring: colors.outlineVariant,
          bezel: colors.outline,
          ink: colors.onSurfaceVariant,
          north: north(theme.brightness),
          needle: colors.primary,
          // The shaded facet: darker than the needle on a light card, lighter
          // on a dark one, so the two halves always part.
          facet: Color.lerp(colors.primary, colors.onSurface, 0.45)!,
          shadow: colors.shadow,
          textDirection: Directionality.of(context),
        ),
      ),
    );
  }
}

class _CompassPainter extends CustomPainter {
  _CompassPainter({
    required this.degrees,
    required this.surface,
    required this.sunken,
    required this.ring,
    required this.bezel,
    required this.ink,
    required this.north,
    required this.needle,
    required this.facet,
    required this.shadow,
    required this.textDirection,
  });
  final double? degrees;
  final Color surface, sunken, ring, bezel, ink, north, needle, facet, shadow;
  final TextDirection textDirection;

  Path _triangle(Offset a, Offset b, Offset c) =>
      Path()
        ..moveTo(a.dx, a.dy)
        ..lineTo(b.dx, b.dy)
        ..lineTo(c.dx, c.dy)
        ..close();

  @override
  void paint(Canvas canvas, Size size) {
    final centre = Offset(size.width / 2, size.height / 2);
    final radius = math.min(size.width, size.height) / 2 - 3;
    if (radius <= 0) return;

    // A soft drop and an opaque bezel lift the instrument off the chart grid.
    canvas.drawCircle(
      centre + Offset(0, radius * 0.05),
      radius + 1,
      Paint()..color = shadow.withValues(alpha: 0.22),
    );
    canvas.drawCircle(
      centre,
      radius,
      Paint()
        ..shader = ui.Gradient.linear(
          Offset(0, centre.dy - radius),
          Offset(0, centre.dy + radius),
          [surface, bezel.withValues(alpha: 0.7)],
        ),
    );
    canvas.drawCircle(
      centre,
      radius,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1
        ..color = bezel,
    );

    final card = radius * 0.84;
    canvas.drawCircle(
      centre,
      card,
      Paint()..shader = ui.Gradient.radial(centre, card, [surface, sunken]),
    );
    canvas.drawCircle(
      centre,
      card,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1
        ..color = ring,
    );

    // North is the fixed red mark on the bezel that the card is read from.
    canvas.drawPath(
      _triangle(
        centre + Offset(0, -card + 1),
        centre + Offset(-radius * 0.1, -radius + 1),
        centre + Offset(radius * 0.1, -radius + 1),
      ),
      Paint()..color = north,
    );

    // Graduations: every 5 degrees when there is room for them, longer at 10
    // and 30, longest at the four cardinal points.
    final step = card >= 24 ? 5 : 10;
    for (var angle = 0; angle < 360; angle += step) {
      final (length, width, colour) =
          angle % 90 == 0
              ? (0.20, 1.6, ink)
              : angle % 30 == 0
              ? (0.14, 1.2, ink.withValues(alpha: 0.85))
              : angle % 10 == 0
              ? (0.09, 1.0, ink.withValues(alpha: 0.65))
              : (0.05, 0.8, ink.withValues(alpha: 0.45));
      final radians = angle * math.pi / 180;
      final direction = Offset(math.sin(radians), -math.cos(radians));
      canvas.drawLine(
        centre + direction * (card * (1 - length)),
        centre + direction * (card - 1.5),
        Paint()
          ..strokeWidth = width
          ..color = angle == 0 ? north : colour,
      );
    }

    // An eight-point rose under everything that moves, faceted light and dark
    // so it reads as relief. Faint, so the needle stays the reading.
    canvas.save();
    canvas.translate(centre.dx, centre.dy);
    for (var angle = 0; angle < 360; angle += 45) {
      final cardinal = angle % 90 == 0;
      final reach = card * (cardinal ? 0.50 : 0.34);
      final half = card * (cardinal ? 0.12 : 0.08);
      canvas.save();
      canvas.rotate(angle * math.pi / 180);
      canvas.drawPath(
        _triangle(Offset(0, -reach), Offset(-half, -half), Offset.zero),
        Paint()..color = ring.withValues(alpha: cardinal ? 0.9 : 0.7),
      );
      canvas.drawPath(
        _triangle(Offset(0, -reach), Offset(half, -half), Offset.zero),
        Paint()..color = ink.withValues(alpha: cardinal ? 0.45 : 0.3),
      );
      canvas.restore();
    }
    canvas.restore();

    for (final entry in const {0: 'N', 90: 'E', 180: 'S', 270: 'W'}.entries) {
      final radians = entry.key * math.pi / 180;
      final direction = Offset(math.sin(radians), -math.cos(radians));
      final painter = TextPainter(
        text: TextSpan(
          text: entry.value,
          style: TextStyle(
            fontSize: math.max(7, card * 0.3),
            height: 1,
            fontWeight: FontWeight.w900,
            color: entry.key == 0 ? north : ink,
          ),
        ),
        textDirection: textDirection,
      )..layout();
      final at = centre + direction * (card * 0.62);
      painter.paint(
        canvas,
        Offset(at.dx - painter.width / 2, at.dy - painter.height / 2),
      );
    }

    if (degrees != null) {
      // A faceted lozenge: the lit half and the shaded half meet on the
      // centreline, so the needle reads as a solid pointer at a glance.
      canvas.save();
      canvas.translate(centre.dx, centre.dy);
      canvas.rotate(degrees! * math.pi / 180);
      final reach = card * 0.80;
      final tail = card * 0.52;
      final half = card * 0.13;
      final outline =
          Paint()
            ..style = PaintingStyle.stroke
            ..strokeWidth = 0.8
            ..color = surface.withValues(alpha: 0.8);
      for (final (path, colour) in [
        (_triangle(Offset(0, -reach), Offset(-half, 0), Offset.zero), needle),
        (_triangle(Offset(0, -reach), Offset(half, 0), Offset.zero), facet),
        (
          _triangle(Offset(0, tail), Offset(-half, 0), Offset.zero),
          ink.withValues(alpha: 0.55),
        ),
        (
          _triangle(Offset(0, tail), Offset(half, 0), Offset.zero),
          ink.withValues(alpha: 0.8),
        ),
      ]) {
        canvas.drawPath(path, Paint()..color = colour);
        canvas.drawPath(path, outline);
      }
      canvas.restore();
    }

    final pivot = card * 0.11;
    canvas.drawCircle(centre, pivot, Paint()..color = surface);
    canvas.drawCircle(
      centre,
      pivot,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = math.max(1, pivot * 0.35)
        ..color = needle,
    );
    canvas.drawCircle(centre, pivot * 0.4, Paint()..color = needle);
  }

  @override
  bool shouldRepaint(_CompassPainter old) =>
      old.degrees != degrees ||
      old.surface != surface ||
      old.sunken != sunken ||
      old.ring != ring ||
      old.bezel != bezel ||
      old.ink != ink ||
      old.north != north ||
      old.needle != needle ||
      old.facet != facet ||
      old.shadow != shadow ||
      old.textDirection != textDirection;
}
