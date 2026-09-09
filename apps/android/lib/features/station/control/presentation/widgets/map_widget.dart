import 'package:prana_mobile/l10n/app_localizations.dart';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:prana_mobile/telemetry/domain/telemetry_repository.dart';

class MapWidget extends StatelessWidget {
  const MapWidget({super.key, required this.position, required this.heading});
  final TelemetryPosition? position;
  final double? heading;
  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          AppLocalizations.of(context).map,
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 10),
        Semantics(
          label:
              '${AppLocalizations.of(context).position}: ${position?.latitude ?? '—'}, ${position?.longitude ?? '—'}',
          child: ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: AspectRatio(
              aspectRatio: 4 / 3,
              child: CustomPaint(
                key: const ValueKey('telemetry-map'),
                painter: TelemetryMapPainter(
                  position,
                  heading,
                  background: colors.surfaceContainerHighest,
                  gridColor: colors.outlineVariant,
                  foreground: colors.onSurface,
                  markerColor: colors.surface,
                  vesselColor: colors.primary,
                ),
              ),
            ),
          ),
        ),
        const SizedBox(height: 8),
        Text(
          AppLocalizations.of(context).mapMockNotice,
          style: TextStyle(color: colors.onSurfaceVariant),
        ),
      ],
    );
  }
}

/// Offline coordinate instrument, deliberately not a geographic basemap.
class TelemetryMapPainter extends CustomPainter {
  TelemetryMapPainter(
    this.position,
    this.heading, {
    this.background = const Color(0xFFE5EFF5),
    this.gridColor = const Color(0xFFB8CEDD),
    this.foreground = const Color(0xFF0D2B4F),
    this.markerColor = Colors.white,
    this.vesselColor = const Color(0xFF123F7E),
  });
  final TelemetryPosition? position;
  final double? heading;
  final Color background, gridColor, foreground, markerColor, vesselColor;
  Offset markerOffset(Size size) {
    final p = position!;
    // Rebase the viewport only after travelling a full coordinate cell.
    final east = (p.longitude - 106.6505) % .003;
    final north = (p.latitude - 10.7615) % .003;
    return Offset(
      20 + east / .003 * (size.width - 40),
      size.height - 20 - north / .003 * (size.height - 40),
    );
  }

  @override
  void paint(Canvas canvas, Size size) {
    canvas.drawRect(Offset.zero & size, Paint()..color = background);
    final grid =
        Paint()
          ..color = gridColor
          ..strokeWidth = 1;
    for (double x = 0; x <= size.width; x += 48) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), grid);
    }
    for (double y = 0; y <= size.height; y += 48) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), grid);
    }
    final north = TextPainter(
      text: TextSpan(
        text: 'N ↑',
        style: TextStyle(
          color: foreground,
          fontSize: 16,
          fontWeight: FontWeight.bold,
        ),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    north.paint(canvas, const Offset(12, 12));
    if (position == null) return;
    final point = markerOffset(size);
    canvas.drawCircle(point, 19, Paint()..color = markerColor);
    canvas.save();
    canvas.translate(point.dx, point.dy);
    canvas.rotate((heading ?? 0) * math.pi / 180);
    final vessel =
        Path()
          ..moveTo(0, -14)
          ..lineTo(10, 12)
          ..lineTo(0, 7)
          ..lineTo(-10, 12)
          ..close();
    canvas.drawPath(vessel, Paint()..color = vesselColor);
    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant TelemetryMapPainter oldDelegate) =>
      oldDelegate.position != position ||
      oldDelegate.heading != heading ||
      oldDelegate.background != background ||
      oldDelegate.gridColor != gridColor ||
      oldDelegate.foreground != foreground ||
      oldDelegate.markerColor != markerColor ||
      oldDelegate.vesselColor != vesselColor;
}
