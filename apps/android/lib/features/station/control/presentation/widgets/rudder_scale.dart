import 'package:flutter/material.dart';

/// How far the helm is over, on the range the state actually allows.
///
/// The scale runs to ±180° because that is where [SteeringState] clamps. A
/// bridge would mark it at the rudder's own limit, but printing 35 here would
/// be a number this simulation cannot honour.
class RudderScale extends StatelessWidget {
  const RudderScale({
    super.key,
    required this.angle,
    required this.enabled,
    required this.portLabel,
    required this.starboardLabel,
  });
  final double angle;
  final bool enabled;
  final String portLabel, starboardLabel;

  static const double limit = 180;

  /// Where the helm sits on the scale: -1 hard to port, 0 amidships, 1 hard to
  /// starboard. Clamped, because the bar has to stay on the bar even if a
  /// caller hands it an angle the state would never produce.
  static double fraction(double angle) => angle.clamp(-limit, limit) / limit;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    final style = theme.textTheme.labelSmall?.copyWith(
      fontWeight: FontWeight.w700,
      letterSpacing: 0.6,
      color: colors.onSurfaceVariant,
    );
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Expanded(child: Text(portLabel, style: style)),
            Text('0', style: style),
            Expanded(
              child: Text(
                starboardLabel,
                textAlign: TextAlign.end,
                style: style,
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        SizedBox(
          height: 16,
          child: CustomPaint(
            painter: _RudderPainter(
              angle: angle,
              track: colors.surfaceContainerHighest,
              tick: colors.outlineVariant,
              fill: enabled ? colors.primary : colors.onSurfaceVariant,
            ),
          ),
        ),
      ],
    );
  }
}

class _RudderPainter extends CustomPainter {
  _RudderPainter({
    required this.angle,
    required this.track,
    required this.tick,
    required this.fill,
  });
  final double angle;
  final Color track, tick, fill;

  @override
  void paint(Canvas canvas, Size size) {
    if (size.width <= 0) return;
    const trackHeight = 6.0;
    final top = (size.height - trackHeight) / 2;
    final middle = size.width / 2;
    final radius = const Radius.circular(3);

    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromLTWH(0, top, size.width, trackHeight),
        radius,
      ),
      Paint()..color = track,
    );

    // Quarter marks, so the bar is read as a scale and not a progress bar.
    for (final fraction in [0.25, 0.75]) {
      canvas.drawRect(
        Rect.fromLTWH(size.width * fraction, top - 3, 1, trackHeight + 6),
        Paint()..color = tick,
      );
    }

    final over = RudderScale.fraction(angle) * middle;
    if (over.abs() > 0.5) {
      canvas.drawRRect(
        RRect.fromRectAndRadius(
          Rect.fromLTWH(
            over < 0 ? middle + over : middle,
            top,
            over.abs(),
            trackHeight,
          ),
          radius,
        ),
        Paint()..color = fill,
      );
    }

    // Amidships mark, drawn over the fill so the centre never disappears.
    canvas.drawRect(
      Rect.fromLTWH(middle - 0.5, top - 4, 1, trackHeight + 8),
      Paint()..color = tick,
    );

    final marker = middle + over;
    canvas.drawCircle(
      Offset(marker.clamp(4.0, size.width - 4), size.height / 2),
      5,
      Paint()..color = fill,
    );
  }

  @override
  bool shouldRepaint(_RudderPainter old) =>
      old.angle != angle ||
      old.track != track ||
      old.tick != tick ||
      old.fill != fill;
}
