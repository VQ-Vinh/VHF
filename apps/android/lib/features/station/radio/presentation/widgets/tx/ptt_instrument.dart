import 'dart:math' as math;

import 'package:flutter/material.dart';

import 'package:prana_mobile/features/station/radio/presentation/widgets/console_palette.dart';

/// What the instrument around the talk key is showing.
enum PttChannelState {
  /// Capture is stopped. Rings only, nothing moves.
  idle,

  /// Capture is running and the channel is quiet.
  listening,

  /// The Station's VAD hears speech on the channel.
  receiving,

  /// The operator is holding the key or a transmission is on air.
  transmit,
}

/// Rings, bearing ticks and state arcs drawn behind the talk key.
///
/// It sits behind the button rather than inside it, so the key itself stays a
/// circle carrying only the mic and its label. Every loop here runs only while
/// the state it depicts is happening, and never under reduced motion: a sweep
/// turning over a stopped capture would say "live" when nothing is.
class PttInstrument extends StatefulWidget {
  const PttInstrument({
    super.key,
    required this.state,
    required this.buttonDiameter,
    required this.outerDiameter,
    required this.child,
  });

  final PttChannelState state;
  final double buttonDiameter;
  final double outerDiameter;
  final Widget child;

  @override
  State<PttInstrument> createState() => _PttInstrumentState();
}

class _PttInstrumentState extends State<PttInstrument>
    with TickerProviderStateMixin {
  late final AnimationController _sweep = AnimationController(
    vsync: this,
    duration: const Duration(seconds: 4),
  );
  late final AnimationController _ripple = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1400),
  );

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _sync();
  }

  @override
  void didUpdateWidget(covariant PttInstrument oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.state != widget.state) _sync();
  }

  void _sync() {
    final still = MediaQuery.maybeOf(context)?.disableAnimations ?? false;
    final live = widget.state != PttChannelState.idle;
    if (live && !still) {
      if (!_sweep.isAnimating) _sweep.repeat();
    } else {
      _sweep.stop();
      _sweep.value = 0;
    }
    if (widget.state == PttChannelState.transmit && !still) {
      if (!_ripple.isAnimating) _ripple.repeat();
    } else {
      _ripple.stop();
      _ripple.value = 0;
    }
  }

  @override
  void dispose() {
    _sweep.dispose();
    _ripple.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final palette = ConsolePalette.of(context);
    return SizedBox.square(
      key: const ValueKey('ptt-instrument'),
      dimension: widget.outerDiameter,
      child: Stack(
        alignment: Alignment.center,
        children: [
          Positioned.fill(
            child: ExcludeSemantics(
              child: AnimatedBuilder(
                animation: Listenable.merge([_sweep, _ripple]),
                builder:
                    (context, _) => CustomPaint(
                      painter: _InstrumentPainter(
                        state: widget.state,
                        buttonRadius: widget.buttonDiameter / 2,
                        sweep: _sweep.value,
                        ripple: _ripple.value,
                        rippling: _ripple.isAnimating,
                        palette: palette,
                      ),
                    ),
              ),
            ),
          ),
          widget.child,
        ],
      ),
    );
  }
}

class _InstrumentPainter extends CustomPainter {
  _InstrumentPainter({
    required this.state,
    required this.buttonRadius,
    required this.sweep,
    required this.ripple,
    required this.rippling,
    required this.palette,
  });

  final PttChannelState state;
  final double buttonRadius;
  final double sweep;
  final double ripple;
  final bool rippling;
  final ConsolePalette palette;

  @override
  void paint(Canvas canvas, Size size) {
    final center = size.center(Offset.zero);
    final outer = size.shortestSide / 2 - 2;
    final gap = outer - buttonRadius;
    // When a large text scale has grown the key into the rings, draw nothing
    // rather than rings crushed against it: the key's text wins.
    if (gap < 10) return;

    final tone = switch (state) {
      PttChannelState.transmit => palette.transmit,
      PttChannelState.idle => palette.muted,
      _ => palette.accent,
    };

    final hairline =
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1
          ..color = palette.hairline;
    canvas.drawCircle(center, outer, hairline);
    canvas.drawCircle(center, buttonRadius + gap * .38, hairline);

    // Sixty bearing ticks, one every six degrees, longer every thirty.
    final tick =
        Paint()
          ..strokeCap = StrokeCap.round
          ..color = palette.muted.withValues(alpha: .55);
    for (var i = 0; i < 60; i++) {
      final major = i % 5 == 0;
      final angle = i * math.pi / 30 - math.pi / 2;
      final unit = Offset(math.cos(angle), math.sin(angle));
      final length = gap * (major ? .26 : .14);
      tick.strokeWidth = major ? 1.6 : 1;
      canvas.drawLine(
        center + unit * (outer - 3),
        center + unit * (outer - 3 - length),
        tick,
      );
    }

    // State arcs: four segments, drawn fuller and brighter as the channel
    // goes from quiet to carrying speech to transmitting.
    final arcRadius = buttonRadius + gap * .62;
    final (span, alpha) = switch (state) {
      PttChannelState.idle => (.30, .35),
      PttChannelState.listening => (.45, .65),
      PttChannelState.receiving => (.80, 1.0),
      PttChannelState.transmit => (.80, 1.0),
    };
    final arc =
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeCap = StrokeCap.round
          ..strokeWidth = math.max(2, gap * .07)
          ..color = tone.withValues(alpha: alpha);
    for (var q = 0; q < 4; q++) {
      final start = q * math.pi / 2 - math.pi / 4 + (1 - span) * math.pi / 4;
      canvas.drawArc(
        Rect.fromCircle(center: center, radius: arcRadius),
        start - math.pi / 2,
        span * math.pi / 2,
        false,
        arc,
      );
    }

    // Sweep, only while live.
    if (state != PttChannelState.idle && sweep > 0) {
      const tail = .6;
      final angle = sweep * 2 * math.pi - math.pi / 2;
      final rect = Rect.fromCircle(center: center, radius: outer);
      // A full-turn gradient rotated to the leading edge, so the fade always
      // runs over the last [tail] radians behind it whatever the angle is.
      canvas.drawArc(
        rect,
        angle - tail,
        tail,
        true,
        Paint()
          ..shader = SweepGradient(
            colors: [
              tone.withValues(alpha: 0),
              tone.withValues(alpha: 0),
              tone.withValues(alpha: .22),
            ],
            stops: const [0, 1 - tail / (2 * math.pi), 1],
            transform: GradientRotation(angle),
          ).createShader(rect),
      );
    }

    // Two rings spreading out from the held key.
    if (state == PttChannelState.transmit && rippling) {
      for (final offset in const [0.0, .5]) {
        final t = (ripple + offset) % 1;
        canvas.drawCircle(
          center,
          buttonRadius + gap * t,
          Paint()
            ..style = PaintingStyle.stroke
            ..strokeWidth = 2
            ..color = palette.transmit.withValues(alpha: (1 - t) * .7),
        );
      }
    }
  }

  @override
  bool shouldRepaint(_InstrumentPainter old) =>
      old.state != state ||
      old.buttonRadius != buttonRadius ||
      old.sweep != sweep ||
      old.ripple != ripple ||
      old.rippling != rippling ||
      old.palette != palette;
}
