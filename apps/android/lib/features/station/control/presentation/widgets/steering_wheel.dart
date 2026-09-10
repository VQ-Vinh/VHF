import 'package:prana_mobile/l10n/app_localizations.dart';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:prana_mobile/core/surfaces.dart';
import '../../application/steering_state.dart';
import 'rudder_scale.dart';

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
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    final enabled =
        widget.active && widget.state.mode == MockControlMode.manual;
    final angle = widget.state.angle;
    final direction =
        angle.abs() < .5
            ? l10n.steeringStraight
            : angle < 0
            ? l10n.steeringLeft
            : l10n.steeringRight;
    final reading = '${angle.toStringAsFixed(0)}°';
    final label = '$reading · $direction';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 10),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  l10n.steeringWheel,
                  style: panelLabelStyle(context),
                ),
              ),
              const SizedBox(width: 8),
              _StateChip(enabled: enabled),
            ],
          ),
        ),
        Container(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 16),
          decoration: panelDecoration(context),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // The angle and the word for it share a line but stay separate
              // widgets: station_workspace_test reads the angle on its own.
              Wrap(
                crossAxisAlignment: WrapCrossAlignment.center,
                alignment: WrapAlignment.center,
                spacing: 12,
                runSpacing: 6,
                children: [
                  Text(
                    reading,
                    key: const ValueKey('steering-angle'),
                    style: TextStyle(
                      fontSize: 40,
                      height: 1.05,
                      fontWeight: FontWeight.w700,
                      letterSpacing: -1,
                      color:
                          enabled ? colors.onSurface : colors.onSurfaceVariant,
                      fontFeatures: const [FontFeature.tabularFigures()],
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 5,
                    ),
                    decoration: BoxDecoration(
                      color: colors.surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(999),
                    ),
                    child: Text(
                      direction,
                      style: theme.textTheme.labelMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                        color: colors.onSurfaceVariant,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              RudderScale(
                angle: angle,
                enabled: enabled,
                portLabel: l10n.steeringLeft,
                starboardLabel: l10n.steeringRight,
              ),
              const SizedBox(height: 14),
              if (!enabled)
                Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Text(
                    l10n.steeringAuto,
                    textAlign: TextAlign.center,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: colors.onSurfaceVariant,
                    ),
                  ),
                ),
              LayoutBuilder(
                builder: (context, constraints) {
                  final diameter = math.min(constraints.maxWidth, 280.0);
                  double bearing(Offset point) => math.atan2(
                    point.dy - diameter / 2,
                    point.dx - diameter / 2,
                  );
                  return Semantics(
                    label: l10n.steeringWheel,
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
                        enabled
                            ? () => _change(() => widget.state.adjust(5))
                            : null,
                    onDecrease:
                        enabled
                            ? () => _change(() => widget.state.adjust(-5))
                            : null,
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
                                widget.state.beginDrag(
                                  bearing(event.localPosition),
                                );
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
                            // The wheel is furniture, not a readout, so it
                            // takes the muted ink. onSurface made it the
                            // brightest thing on a dark bridge at night.
                            foreground: colors.onSurfaceVariant,
                            disabled: colors.onSurfaceVariant.withValues(
                              alpha: 0.45,
                            ),
                            accent: colors.primary,
                            face: colors.surfaceContainerHighest,
                            rim: colors.outlineVariant,
                          ),
                        ),
                      ),
                    ),
                  );
                },
              ),
              const SizedBox(height: 14),
              Row(
                children: [
                  _NudgeButton(
                    buttonKey: const ValueKey('steering-left'),
                    tooltip: l10n.steeringLeft,
                    icon: Icons.rotate_left,
                    onPressed:
                        enabled
                            ? () => _change(() => widget.state.adjust(-5))
                            : null,
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: OutlinedButton.icon(
                      key: const ValueKey('steering-center'),
                      style: OutlinedButton.styleFrom(
                        minimumSize: const Size(48, 48),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                      onPressed:
                          enabled ? () => _change(widget.state.center) : null,
                      icon: const Icon(Icons.adjust, size: 18),
                      label: Text(
                        l10n.steeringCenter,
                        textAlign: TextAlign.center,
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  _NudgeButton(
                    buttonKey: const ValueKey('steering-right'),
                    tooltip: l10n.steeringRight,
                    icon: Icons.rotate_right,
                    onPressed:
                        enabled
                            ? () => _change(() => widget.state.adjust(5))
                            : null,
                  ),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }
}

/// Kept an [IconButton] behind its own widget: control_test reads this key
/// back as an IconButton to check that Auto disables the nudge.
class _NudgeButton extends StatelessWidget {
  const _NudgeButton({
    required this.buttonKey,
    required this.tooltip,
    required this.icon,
    required this.onPressed,
  });
  final Key buttonKey;
  final String tooltip;
  final IconData icon;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return IconButton(
      key: buttonKey,
      tooltip: tooltip,
      constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
      style: IconButton.styleFrom(
        backgroundColor: colors.surfaceContainerHighest,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
      onPressed: onPressed,
      icon: Icon(icon),
    );
  }
}

class _StateChip extends StatelessWidget {
  const _StateChip({required this.enabled});
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
      decoration: BoxDecoration(
        color:
            enabled ? colors.primaryContainer : colors.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        enabled ? l10n.manual : l10n.auto,
        style: theme.textTheme.labelSmall?.copyWith(
          fontWeight: FontWeight.w800,
          letterSpacing: 0.6,
          color: enabled ? colors.onPrimaryContainer : colors.onSurfaceVariant,
        ),
      ),
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
    required this.face,
    required this.rim,
  });
  final double angle;
  final bool enabled;
  final Color foreground, disabled, accent, face, rim;

  @override
  void paint(Canvas canvas, Size size) {
    final center = size.center(Offset.zero);
    final radius = size.shortestSide * .38;
    final ink = enabled ? foreground : disabled;
    final live = enabled ? accent : disabled;

    canvas.save();
    canvas.translate(center.dx, center.dy);

    // Fixed bezel. It does not turn with the wheel, so it is what the angle is
    // read against; without it a symmetric wheel gives no sense of how far over
    // the helm is.
    canvas.drawCircle(
      Offset.zero,
      radius * 1.28,
      Paint()..color = face.withValues(alpha: 0.55),
    );
    final ticks =
        Paint()
          ..color = rim
          ..strokeWidth = 1
          ..strokeCap = StrokeCap.round;
    for (var degrees = 0; degrees < 360; degrees += 15) {
      final major = degrees % 45 == 0;
      final radians = (degrees - 90) * math.pi / 180;
      final unit = Offset(math.cos(radians), math.sin(radians));
      canvas.drawLine(
        unit * (radius * (major ? 1.16 : 1.20)),
        unit * (radius * 1.26),
        ticks..strokeWidth = major ? 1.6 : 1,
      );
    }

    // How far over from amidships, drawn on the fixed layer.
    if (angle.abs() > .5) {
      canvas.drawArc(
        Rect.fromCircle(center: Offset.zero, radius: radius * 1.22),
        -math.pi / 2,
        angle * math.pi / 180,
        false,
        Paint()
          ..color = live.withValues(alpha: 0.75)
          ..strokeWidth = 3
          ..strokeCap = StrokeCap.round
          ..style = PaintingStyle.stroke,
      );
    }

    // Index mark at amidships.
    final index =
        Path()
          ..moveTo(0, -radius * 1.34)
          ..lineTo(-4.5, -radius * 1.44)
          ..lineTo(4.5, -radius * 1.44)
          ..close();
    canvas.drawPath(index, Paint()..color = live);

    canvas.rotate(angle * math.pi / 180);

    final spoke =
        Paint()
          ..color = ink
          ..strokeWidth = radius * .075
          ..strokeCap = StrokeCap.round
          ..style = PaintingStyle.stroke;
    for (var i = 0; i < 8; i++) {
      final radians = i * math.pi / 4;
      canvas.drawLine(
        Offset.zero,
        Offset(math.cos(radians), math.sin(radians)) * radius,
        spoke,
      );
    }
    canvas.drawCircle(
      Offset.zero,
      radius,
      Paint()
        ..color = ink
        ..strokeWidth = radius * .11
        ..style = PaintingStyle.stroke,
    );

    // Handles, and a longer one on the king spoke so the wheel reads as turned
    // even at a glance.
    for (var i = 0; i < 8; i++) {
      final radians = (i * math.pi / 4) - math.pi / 2;
      final king = i == 0;
      final unit = Offset(math.cos(radians), math.sin(radians));
      canvas.drawLine(
        unit * radius,
        unit * (radius * (king ? 1.16 : 1.10)),
        Paint()
          ..color = king ? live : ink
          ..strokeWidth = radius * (king ? .11 : .08)
          ..strokeCap = StrokeCap.round,
      );
    }

    canvas.drawCircle(Offset.zero, radius * .22, Paint()..color = live);
    canvas.drawCircle(Offset.zero, radius * .10, Paint()..color = face);
    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant _WheelPainter old) =>
      angle != old.angle ||
      enabled != old.enabled ||
      foreground != old.foreground ||
      disabled != old.disabled ||
      accent != old.accent ||
      face != old.face ||
      rim != old.rim;
}
