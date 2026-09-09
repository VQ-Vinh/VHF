import 'package:prana_mobile/l10n/app_localizations.dart';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../../application/steering_state.dart';

class SteeringWheel extends StatefulWidget {
  const SteeringWheel({
    super.key,
    required this.state,
    required this.active,
    required this.onChanged,
  });
  final SteeringState state;
  final bool active;
  final VoidCallback onChanged;
  @override
  State<SteeringWheel> createState() => _SteeringWheelState();
}

class _SteeringWheelState extends State<SteeringWheel> {
  int? _pointer;
  @override
  void didUpdateWidget(covariant SteeringWheel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!widget.active || widget.state.mode == MockControlMode.auto) _end();
  }

  void _end() {
    _pointer = null;
    widget.state.endDrag();
  }

  void _change(VoidCallback action) {
    action();
    widget.onChanged();
  }

  @override
  void dispose() {
    _end();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final enabled =
        widget.active && widget.state.mode == MockControlMode.manual;
    final angle = widget.state.angle;
    final direction =
        angle.abs() < .5
            ? AppLocalizations.of(context).steeringStraight
            : angle < 0
            ? AppLocalizations.of(context).steeringLeft
            : AppLocalizations.of(context).steeringRight;
    final label = '${angle.toStringAsFixed(0)}° · $direction';
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          AppLocalizations.of(context).steeringWheel,
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 12),
        Text(label, key: const ValueKey('steering-angle')),
        if (!enabled) Text(AppLocalizations.of(context).steeringAuto),
        LayoutBuilder(
          builder: (context, constraints) {
            final diameter = math.min(constraints.maxWidth, 320.0);
            double bearing(Offset point) =>
                math.atan2(point.dy - diameter / 2, point.dx - diameter / 2);
            return Semantics(
              label: AppLocalizations.of(context).steeringWheel,
              value: label,
              increasedValue:
                  enabled
                      ? '${(angle + 5).clamp(-180, 180).toStringAsFixed(0)}°'
                      : null,
              decreasedValue:
                  enabled
                      ? '${(angle - 5).clamp(-180, 180).toStringAsFixed(0)}°'
                      : null,
              onIncrease:
                  enabled ? () => _change(() => widget.state.adjust(5)) : null,
              onDecrease:
                  enabled ? () => _change(() => widget.state.adjust(-5)) : null,
              child: GestureDetector(
                key: const ValueKey('steering-wheel'),
                behavior: HitTestBehavior.opaque,
                onPanStart:
                    enabled
                        ? (event) {
                          if ((event.localPosition -
                                      Offset(diameter / 2, diameter / 2))
                                  .distance <
                              diameter * .12) {
                            return;
                          }
                          _pointer = 0;
                          widget.state.beginDrag(bearing(event.localPosition));
                        }
                        : null,
                onPanUpdate:
                    enabled
                        ? (event) {
                          if (_pointer != null) {
                            _change(
                              () => widget.state.drag(
                                bearing(event.localPosition),
                              ),
                            );
                          }
                        }
                        : null,
                onPanEnd: enabled ? (_) => _end() : null,
                onPanCancel: enabled ? _end : null,
                child: SizedBox.square(
                  dimension: diameter,
                  child: CustomPaint(
                    painter: _WheelPainter(
                      angle,
                      enabled,
                      foreground: Theme.of(context).colorScheme.onSurface,
                      disabled: Theme.of(context).colorScheme.onSurfaceVariant,
                      accent: Theme.of(context).colorScheme.primary,
                    ),
                  ),
                ),
              ),
            );
          },
        ),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          alignment: WrapAlignment.center,
          children: [
            IconButton(
              key: const ValueKey('steering-left'),
              tooltip: AppLocalizations.of(context).steeringLeft,
              constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
              onPressed:
                  enabled ? () => _change(() => widget.state.adjust(-5)) : null,
              icon: const Icon(Icons.rotate_left),
            ),
            OutlinedButton(
              key: const ValueKey('steering-center'),
              style: OutlinedButton.styleFrom(minimumSize: const Size(48, 48)),
              onPressed: enabled ? () => _change(widget.state.center) : null,
              child: Text(AppLocalizations.of(context).steeringCenter),
            ),
            IconButton(
              key: const ValueKey('steering-right'),
              tooltip: AppLocalizations.of(context).steeringRight,
              constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
              onPressed:
                  enabled ? () => _change(() => widget.state.adjust(5)) : null,
              icon: const Icon(Icons.rotate_right),
            ),
          ],
        ),
      ],
    );
  }
}

class _WheelPainter extends CustomPainter {
  const _WheelPainter(
    this.angle,
    this.enabled, {
    required this.foreground,
    required this.disabled,
    required this.accent,
  });
  final double angle;
  final bool enabled;
  final Color foreground, disabled, accent;
  @override
  void paint(Canvas canvas, Size size) {
    final center = size.center(Offset.zero);
    final radius = size.shortestSide * .38;
    final paint =
        Paint()
          ..color = enabled ? foreground : disabled
          ..strokeWidth = radius * .13
          ..strokeCap = StrokeCap.round
          ..style = PaintingStyle.stroke;
    canvas.save();
    canvas.translate(center.dx, center.dy);
    canvas.rotate(angle * math.pi / 180);
    canvas.drawCircle(Offset.zero, radius, paint);
    for (final bearing in [0.0, math.pi, math.pi / 2]) {
      canvas.drawLine(
        Offset.zero,
        Offset(math.cos(bearing), math.sin(bearing)) * radius,
        paint,
      );
    }
    paint
      ..style = PaintingStyle.fill
      ..color = accent;
    canvas.drawCircle(Offset.zero, radius * .22, paint);
    canvas.drawCircle(Offset(0, -radius), radius * .09, paint);
    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant _WheelPainter old) =>
      angle != old.angle ||
      enabled != old.enabled ||
      foreground != old.foreground ||
      disabled != old.disabled ||
      accent != old.accent;
}
