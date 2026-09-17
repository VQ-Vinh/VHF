import 'package:prana_mobile/l10n/app_localizations.dart';
import 'dart:math' as math;
import 'dart:ui' as ui;
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
                            // The wheel is furniture, not a readout: wood and
                            // brass, held a stop darker in the dark theme so
                            // it is never the brightest thing on the bridge.
                            materials:
                                theme.brightness == Brightness.dark
                                    ? _WheelMaterials.dark
                                    : _WheelMaterials.light,
                            muted: colors.onSurfaceVariant,
                            accent: colors.primary,
                            face: colors.surfaceContainerHighest,
                            rim: colors.outlineVariant,
                            shadow: colors.shadow,
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

/// Wood and brass for the wheel, the same values as the desktop's `wheel_*`
/// theme tokens.
class _WheelMaterials {
  const _WheelMaterials({
    required this.wood,
    required this.woodLight,
    required this.woodShade,
    required this.brass,
    required this.brassLight,
    required this.brassShade,
  });
  final Color wood, woodLight, woodShade, brass, brassLight, brassShade;

  static const light = _WheelMaterials(
    wood: Color(0xFF8B5A2B),
    woodLight: Color(0xFFB98352),
    woodShade: Color(0xFF5C3A1A),
    brass: Color(0xFFC49A3A),
    brassLight: Color(0xFFF0D78C),
    brassShade: Color(0xFF7A5C1E),
  );

  static const dark = _WheelMaterials(
    wood: Color(0xFF6E4724),
    woodLight: Color(0xFF946640),
    woodShade: Color(0xFF3A2510),
    brass: Color(0xFFA5823A),
    brassLight: Color(0xFFD2BA78),
    brassShade: Color(0xFF5E4719),
  );
}

// Wheel proportions, as fractions of the wheel radius.
const _rimInner = 0.86;
const _rimOuter = 1.0;
const _hub = 0.29;

/// A spoke's half-width along its length: the taper out from the hub with a
/// bead near it, then the handle's collar, neck and grip beyond the rim.
const _armProfile = <List<double>>[
  [0.20, 0.056],
  [0.30, 0.046],
  [0.345, 0.060],
  [0.39, 0.044],
  [0.86, 0.030],
  [1.00, 0.032],
  [1.035, 0.052],
  [1.065, 0.030],
  [1.10, 0.036],
  [1.16, 0.058],
  [1.205, 0.046],
  [1.235, 0.026],
  [1.248, 0.0],
];

/// One spoke and its handle lying along +x, eased between profile stations.
Path _armPath(double radius) {
  final edge = <Offset>[];
  for (var i = 0; i < _armProfile.length - 1; i++) {
    final [x0, w0] = _armProfile[i];
    final [x1, w1] = _armProfile[i + 1];
    for (var step = 0; step < 6; step++) {
      final t = step / 6;
      edge.add(
        Offset(x0 + (x1 - x0) * t, w0 + (w1 - w0) * t * t * (3 - 2 * t)),
      );
    }
  }
  edge.add(Offset(_armProfile.last[0], _armProfile.last[1]));
  final path = Path()..moveTo(edge.first.dx * radius, -edge.first.dy * radius);
  for (final point in edge.skip(1)) {
    path.lineTo(point.dx * radius, -point.dy * radius);
  }
  for (final point in edge.reversed) {
    path.lineTo(point.dx * radius, point.dy * radius);
  }
  return path..close();
}

class _WheelPainter extends CustomPainter {
  const _WheelPainter(
    this.angle,
    this.enabled, {
    required this.materials,
    required this.muted,
    required this.accent,
    required this.face,
    required this.rim,
    required this.shadow,
  });
  final double angle;
  final bool enabled;
  final _WheelMaterials materials;
  final Color muted, accent, face, rim, shadow;

  /// Wood or brass, washed toward the muted ink while the helm is locked.
  Color _material(Color colour, [double alpha = 1]) =>
      enabled
          ? colour.withValues(alpha: alpha)
          : Color.lerp(colour, muted, .7)!.withValues(alpha: alpha * .5);

  /// A domed brass disc lit from the upper left, however far the wheel is
  /// turned.
  void _brassDisc(Canvas canvas, Offset at, double size) {
    // The canvas turns with the wheel; turn the light back so it stays put.
    final light = (-135 - angle) * math.pi / 180;
    final focus = at + Offset(math.cos(light), math.sin(light)) * (size * .45);
    canvas.drawCircle(
      at,
      size,
      Paint()
        ..shader = ui.Gradient.radial(
          at,
          size,
          [
            _material(materials.brassLight),
            _material(materials.brass),
            _material(materials.brassShade),
          ],
          const [0, .55, 1],
          TileMode.clamp,
          null,
          focus,
        ),
    );
    canvas.drawCircle(
      at,
      size,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = math.max(.6, size * .08)
        ..color = _material(materials.brassShade),
    );
  }

  @override
  void paint(Canvas canvas, Size size) {
    final center = size.center(Offset.zero);
    final radius = size.shortestSide * .38;
    final live = enabled ? accent : muted.withValues(alpha: 0.45);
    final set = materials;

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
          ..color = live.withValues(alpha: enabled ? 0.75 : 0.34)
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

    final arm = _armPath(radius);
    final rimPath =
        Path()
          ..fillType = PathFillType.evenOdd
          ..addOval(
            Rect.fromCircle(center: Offset.zero, radius: radius * _rimOuter),
          )
          ..addOval(
            Rect.fromCircle(center: Offset.zero, radius: radius * _rimInner),
          );

    // Cast shadow, down and right of a light above the console.
    final cast = Paint()..color = shadow.withValues(alpha: enabled ? .22 : .08);
    canvas.save();
    canvas.translate(radius * .03, radius * .05);
    canvas.rotate(angle * math.pi / 180);
    for (var i = 0; i < 8; i++) {
      canvas.save();
      canvas.rotate((i * 45 - 90) * math.pi / 180);
      canvas.drawPath(arm, cast);
      canvas.restore();
    }
    canvas.drawPath(rimPath, cast);
    canvas.drawCircle(Offset.zero, radius * _hub, cast);
    canvas.restore();

    canvas.rotate(angle * math.pi / 180);
    final hairline = math.max(.8, radius * .006);
    final edge =
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = hairline
          ..color = _material(set.woodShade);

    // Turned spokes, each running out through the rim into a handle. The
    // gradient runs across the spoke, so it reads as round and not flat.
    final across =
        Paint()
          ..shader = ui.Gradient.linear(
            Offset(0, -radius * .06),
            Offset(0, radius * .06),
            [
              _material(set.woodShade),
              _material(set.woodLight),
              _material(set.wood),
              _material(set.woodShade),
            ],
            const [0, .32, .55, 1],
          );
    for (var i = 0; i < 8; i++) {
      canvas.save();
      canvas.rotate((i * 45 - 90) * math.pi / 180);
      canvas.drawPath(arm, across);
      canvas.drawPath(arm, edge);
      if (i == 0) {
        // The king spoke wears a turk's head, so amidships is found by eye as
        // it is by hand on a real helm.
        final band = RRect.fromRectAndRadius(
          Rect.fromLTWH(
            radius * 1.055,
            -radius * .045,
            radius * .05,
            radius * .09,
          ),
          Radius.circular(radius * .012),
        );
        canvas.drawRRect(band, Paint()..color = live);
        canvas.drawRRect(
          band,
          Paint()
            ..style = PaintingStyle.stroke
            ..strokeWidth = hairline
            ..color = shadow.withValues(alpha: .35),
        );
      }
      canvas.restore();
    }

    // The rim: lit along its crown and dark at both edges.
    const inner = _rimInner / _rimOuter;
    canvas.drawPath(
      rimPath,
      Paint()
        ..shader = ui.Gradient.radial(
          Offset.zero,
          radius * _rimOuter,
          [
            _material(set.woodShade),
            _material(set.woodShade),
            _material(set.wood),
            _material(set.woodLight),
            _material(set.wood),
            _material(set.woodShade),
          ],
          const [
            0,
            inner,
            inner + (1 - inner) * .30,
            inner + (1 - inner) * .55,
            inner + (1 - inner) * .80,
            1,
          ],
        ),
    );
    canvas.drawPath(rimPath, edge);

    // Grain, and the joints between the rim's eight sections. Both turn with
    // the wheel, which is what makes a small turn visible.
    final grain =
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeCap = StrokeCap.round
          ..strokeWidth = math.max(.6, radius * .005)
          ..color = _material(set.woodShade, .45);
    const lanes = [.895, .955];
    const sweeps = [26, 18];
    for (var section = 0; section < 8; section++) {
      for (var lane = 0; lane < lanes.length; lane++) {
        final begin = section * 45 + 8 + lane * 14;
        // Mirrors Qt's anticlockwise arcs, so both apps grain the same way.
        canvas.drawArc(
          Rect.fromCircle(center: Offset.zero, radius: radius * lanes[lane]),
          -(begin + sweeps[lane]) * math.pi / 180,
          sweeps[lane] * math.pi / 180,
          false,
          grain,
        );
      }
    }
    final joint =
        Paint()
          ..strokeWidth = math.max(.8, radius * .008)
          ..color = _material(set.woodShade, .85);
    for (var section = 0; section < 8; section++) {
      final radians = (section * 45 + 22.5) * math.pi / 180;
      final unit = Offset(math.cos(radians), math.sin(radians));
      canvas.drawLine(
        unit * (radius * _rimInner),
        unit * (radius * _rimOuter),
        joint,
      );
    }

    // Brass studs where each spoke passes through the rim.
    final middle = radius * (_rimInner + _rimOuter) / 2;
    for (var i = 0; i < 8; i++) {
      final radians = i * math.pi / 4;
      _brassDisc(
        canvas,
        Offset(math.cos(radians), math.sin(radians)) * middle,
        radius * .03,
      );
    }

    // Hub: a wooden boss under a brass plate held by eight bolts.
    canvas.drawCircle(
      Offset.zero,
      radius * _hub,
      Paint()
        ..shader = ui.Gradient.radial(
          Offset.zero,
          radius * _hub,
          [
            _material(set.woodLight),
            _material(set.wood),
            _material(set.woodShade),
          ],
          const [0, .75, 1],
        ),
    );
    canvas.drawCircle(Offset.zero, radius * _hub, edge);
    _brassDisc(canvas, Offset.zero, radius * .21);
    final bolt = Paint()..color = _material(set.brassShade);
    for (var i = 0; i < 8; i++) {
      final radians = (i * 45 + 22.5) * math.pi / 180;
      canvas.drawCircle(
        Offset(math.cos(radians), math.sin(radians)) * (radius * .155),
        radius * .02,
        bolt,
      );
    }
    canvas.drawCircle(Offset.zero, radius * .075, Paint()..color = live);
    canvas.drawCircle(
      Offset.zero,
      radius * .075,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = math.max(.8, radius * .008)
        ..color = _material(set.brassShade),
    );
    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant _WheelPainter old) =>
      angle != old.angle ||
      enabled != old.enabled ||
      materials != old.materials ||
      muted != old.muted ||
      accent != old.accent ||
      face != old.face ||
      rim != old.rim ||
      shadow != old.shadow;
}
