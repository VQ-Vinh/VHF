import 'package:prana_mobile/l10n/app_localizations.dart';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:prana_mobile/core/surfaces.dart';
import 'package:prana_mobile/telemetry/domain/telemetry_repository.dart';
import 'sim_notice.dart';

class MapWidget extends StatelessWidget {
  const MapWidget({
    super.key,
    required this.position,
    required this.heading,
    this.track = const [],
  });
  final TelemetryPosition? position;
  final double? heading;

  /// Recent fixes, oldest first. Drawn as the track behind the vessel.
  final List<TelemetryPosition> track;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 10),
          child: Text(l10n.map, style: panelLabelStyle(context)),
        ),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: panelDecoration(context),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Semantics(
                label:
                    '${l10n.position}: '
                    '${position?.latitude ?? '—'}, ${position?.longitude ?? '—'}',
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(10),
                  child: AspectRatio(
                    aspectRatio: 4 / 3,
                    child: CustomPaint(
                      key: const ValueKey('telemetry-map'),
                      painter: TelemetryMapPainter(
                        position,
                        heading,
                        track: track,
                        background: colors.surfaceContainerHighest,
                        gridColor: colors.outlineVariant,
                        foreground: colors.onSurface,
                        markerColor: colors.surface,
                        vesselColor: colors.primary,
                        trackColor: colors.primary.withValues(alpha: 0.55),
                        badgeColor: colors.surface.withValues(alpha: 0.86),
                        textDirection: Directionality.of(context),
                      ),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 10),
              SimNotice(
                icon: Icons.warning_amber_rounded,
                message: l10n.mapMockNotice,
              ),
            ],
          ),
        ),
      ],
    );
  }
}

/// Offline coordinate instrument, deliberately not a geographic basemap.
///
/// The viewport is one 0.003° cell. The grid divides that cell into sixths so
/// a square is a fixed distance rather than a fixed number of pixels, which is
/// what lets the scale bar mean anything.
class TelemetryMapPainter extends CustomPainter {
  TelemetryMapPainter(
    this.position,
    this.heading, {
    this.track = const [],
    this.background = const Color(0xFFE5EFF5),
    this.gridColor = const Color(0xFFB8CEDD),
    this.foreground = const Color(0xFF0D2B4F),
    this.markerColor = Colors.white,
    this.vesselColor = const Color(0xFF123F7E),
    this.trackColor = const Color(0x8C123F7E),
    this.badgeColor = const Color(0xDBFFFFFF),
    this.textDirection = TextDirection.ltr,
  });
  final TelemetryPosition? position;
  final double? heading;
  final List<TelemetryPosition> track;
  final Color background,
      gridColor,
      foreground,
      markerColor,
      vesselColor,
      trackColor,
      badgeColor;
  final TextDirection textDirection;

  static const double _cell = .003;
  static const double _divisions = 6;
  static const double _inset = 20;

  Offset markerOffset(Size size) => _offset(position!, size);

  Offset _offset(TelemetryPosition p, Size size) {
    // Rebase the viewport only after travelling a full coordinate cell.
    final east = (p.longitude - 106.6505) % _cell;
    final north = (p.latitude - 10.7615) % _cell;
    return Offset(
      _inset + east / _cell * (size.width - _inset * 2),
      size.height - _inset - north / _cell * (size.height - _inset * 2),
    );
  }

  /// Metres across one grid division at this latitude.
  double get _divisionMetres {
    final latitude = position?.latitude ?? 10.7615;
    return _cell / _divisions * 111320 * math.cos(latitude * math.pi / 180);
  }

  TextPainter _text(
    String value,
    double size,
    Color color,
    FontWeight weight,
  ) => TextPainter(
    text: TextSpan(
      text: value,
      style: TextStyle(
        color: color,
        fontSize: size,
        height: 1.1,
        fontWeight: weight,
      ),
    ),
    textDirection: textDirection,
  )..layout();

  void _badge(Canvas canvas, Offset topLeft, TextPainter text) {
    final rect = Rect.fromLTWH(
      topLeft.dx,
      topLeft.dy,
      text.width + 14,
      text.height + 10,
    );
    canvas.drawRRect(
      RRect.fromRectAndRadius(rect, const Radius.circular(6)),
      Paint()..color = badgeColor,
    );
    text.paint(canvas, Offset(rect.left + 7, rect.top + 5));
  }

  @override
  void paint(Canvas canvas, Size size) {
    canvas.drawRect(Offset.zero & size, Paint()..color = background);

    final grid =
        Paint()
          ..color = gridColor
          ..strokeWidth = 1;
    final span = Size(size.width - _inset * 2, size.height - _inset * 2);
    for (var i = 0; i <= _divisions; i++) {
      final x = _inset + span.width * i / _divisions;
      final y = _inset + span.height * i / _divisions;
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), grid);
      canvas.drawLine(Offset(0, y), Offset(size.width, y), grid);
    }

    _badge(
      canvas,
      const Offset(10, 10),
      _text('↑ N', 12, foreground, FontWeight.w700),
    );
    _scaleBar(canvas, size);

    if (position != null && heading != null) {
      final label = _text(
        'HDG ${heading!.round().toString().padLeft(3, '0')}°',
        11,
        foreground,
        FontWeight.w700,
      );
      _badge(canvas, Offset(size.width - label.width - 24, 10), label);
    }

    if (position == null) return;
    _track(canvas, size);

    final point = markerOffset(size);
    canvas.drawCircle(point, 19, Paint()..color = markerColor);
    canvas.drawCircle(
      point,
      19,
      Paint()
        ..color = vesselColor.withValues(alpha: 0.35)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.5,
    );
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

  /// The track, split wherever the viewport rebased. Joining across a cell
  /// boundary would draw a line straight back across the chart that the vessel
  /// never sailed.
  void _track(Canvas canvas, Size size) {
    if (track.length < 2) return;
    final paint =
        Paint()
          ..color = trackColor
          ..strokeWidth = 2
          ..strokeCap = StrokeCap.round
          ..strokeJoin = StrokeJoin.round
          ..style = PaintingStyle.stroke;
    final limit = math.min(size.width, size.height) / 2;
    var path = Path();
    var started = false;
    Offset? last;
    for (final fix in track) {
      final point = _offset(fix, size);
      if (!started || (last != null && (point - last).distance > limit)) {
        if (started) canvas.drawPath(path, paint);
        path = Path()..moveTo(point.dx, point.dy);
        started = true;
      } else {
        path.lineTo(point.dx, point.dy);
      }
      last = point;
    }
    canvas.drawPath(path, paint);
  }

  void _scaleBar(Canvas canvas, Size size) {
    final length = (size.width - _inset * 2) / _divisions;
    final left = 12.0;
    final bottom = size.height - 14;
    final bar =
        Paint()
          ..color = foreground
          ..strokeWidth = 2
          ..strokeCap = StrokeCap.square;
    canvas.drawLine(Offset(left, bottom), Offset(left + length, bottom), bar);
    for (final x in [left, left + length]) {
      canvas.drawLine(Offset(x, bottom - 4), Offset(x, bottom), bar);
    }
    _text(
      '${_divisionMetres.round()} m',
      10,
      foreground,
      FontWeight.w600,
    ).paint(canvas, Offset(left, bottom - 17));
  }

  @override
  bool shouldRepaint(covariant TelemetryMapPainter oldDelegate) =>
      oldDelegate.position != position ||
      oldDelegate.heading != heading ||
      oldDelegate.track.length != track.length ||
      oldDelegate.background != background ||
      oldDelegate.gridColor != gridColor ||
      oldDelegate.foreground != foreground ||
      oldDelegate.markerColor != markerColor ||
      oldDelegate.vesselColor != vesselColor ||
      oldDelegate.trackColor != trackColor ||
      oldDelegate.badgeColor != badgeColor ||
      oldDelegate.textDirection != textDirection;
}
