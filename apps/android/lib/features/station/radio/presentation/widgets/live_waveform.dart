import 'dart:math' as math;

import 'package:flutter/material.dart';

import 'console_palette.dart';

/// The idle picture for the Live Transmission module.
///
/// It is not a level meter: the phone receives no audio level from the
/// Station. It moves only while capture is running, when "waiting for speech"
/// is true, and lies flat when capture is stopped, when it is not.
class LiveWaveform extends StatefulWidget {
  const LiveWaveform({super.key, required this.listening, this.height = 40});
  final bool listening;
  final double height;

  @override
  State<LiveWaveform> createState() => _LiveWaveformState();
}

class _LiveWaveformState extends State<LiveWaveform>
    with SingleTickerProviderStateMixin {
  late final AnimationController _phase = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1600),
  );

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _sync();
  }

  @override
  void didUpdateWidget(covariant LiveWaveform oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.listening != widget.listening) _sync();
  }

  void _sync() {
    final still = MediaQuery.maybeOf(context)?.disableAnimations ?? false;
    if (widget.listening && !still) {
      if (!_phase.isAnimating) _phase.repeat();
    } else {
      _phase.stop();
      _phase.value = 0;
    }
  }

  @override
  void dispose() {
    _phase.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final palette = ConsolePalette.of(context);
    return ExcludeSemantics(
      child: SizedBox(
        key: const ValueKey('live-waveform'),
        width: 96,
        height: widget.height,
        child: AnimatedBuilder(
          animation: _phase,
          builder:
              (context, _) => CustomPaint(
                painter: _WavePainter(
                  phase: _phase.value,
                  live: widget.listening,
                  color: widget.listening ? palette.accent : palette.muted,
                ),
              ),
        ),
      ),
    );
  }
}

class _WavePainter extends CustomPainter {
  _WavePainter({required this.phase, required this.live, required this.color});
  final double phase;
  final bool live;
  final Color color;

  static const _bars = 11;

  @override
  void paint(Canvas canvas, Size size) {
    final slot = size.width / _bars;
    final paint =
        Paint()
          ..color = color
          ..strokeCap = StrokeCap.round
          ..strokeWidth = math.min(3, slot * .45);
    final middle = size.height / 2;
    for (var i = 0; i < _bars; i++) {
      // A bell of heights, centre tallest, rippling outward over time.
      final bell = math.exp(-math.pow((i - (_bars - 1) / 2) / 2.6, 2));
      final wave =
          live
              ? .55 + .45 * math.sin((phase * 2 + i / _bars) * 2 * math.pi)
              : 0;
      final half = math.max(
        1.5,
        (size.height / 2 - 2) * bell * (live ? wave : .12),
      );
      final x = slot * (i + .5);
      canvas.drawLine(
        Offset(x, middle - half),
        Offset(x, middle + half),
        paint,
      );
    }
  }

  @override
  bool shouldRepaint(_WavePainter old) =>
      old.phase != phase || old.live != live || old.color != color;
}
