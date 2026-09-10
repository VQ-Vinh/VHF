import 'package:flutter/material.dart';

/// Recent speed samples as a bar trend.
///
/// A bounded graphic, like the Control map and wheel: it keeps its height at
/// every text scale rather than growing with type, because a chart that grows
/// with the font stops fitting the card it explains.
class SpeedTrend extends StatelessWidget {
  const SpeedTrend({super.key, required this.values, this.height = 34});
  final List<double> values;
  final double height;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return SizedBox(
      height: height,
      width: double.infinity,
      child: CustomPaint(
        painter: _SpeedTrendPainter(
          values: values,
          bar: colors.primary.withValues(alpha: 0.28),
          latest: colors.primary,
        ),
      ),
    );
  }
}

class _SpeedTrendPainter extends CustomPainter {
  _SpeedTrendPainter({
    required this.values,
    required this.bar,
    required this.latest,
  });
  final List<double> values;
  final Color bar, latest;

  @override
  void paint(Canvas canvas, Size size) {
    if (values.isEmpty || size.width <= 0) return;

    // Show at most what fits at a readable bar width, newest last.
    const slot = 7.0;
    final capacity = (size.width / slot).floor().clamp(1, values.length);
    final window = values.sublist(values.length - capacity);

    var low = window.reduce((a, b) => a < b ? a : b);
    var high = window.reduce((a, b) => a > b ? a : b);
    // A flat reading would otherwise divide by zero and draw nothing; give it
    // a band so it renders as a steady mid-height line.
    if (high - low < 0.01) {
      low -= 0.5;
      high += 0.5;
    }

    final width = size.width / window.length;
    final barWidth = (width * 0.62).clamp(1.5, 6.0);
    for (var i = 0; i < window.length; i++) {
      final t = ((window[i] - low) / (high - low)).clamp(0.0, 1.0);
      final barHeight = (size.height * (0.18 + 0.82 * t)).clamp(
        2.0,
        size.height,
      );
      final left = i * width + (width - barWidth) / 2;
      canvas.drawRRect(
        RRect.fromRectAndRadius(
          Rect.fromLTWH(left, size.height - barHeight, barWidth, barHeight),
          const Radius.circular(1.5),
        ),
        Paint()..color = i == window.length - 1 ? latest : bar,
      );
    }
  }

  @override
  bool shouldRepaint(_SpeedTrendPainter old) =>
      old.bar != bar ||
      old.latest != latest ||
      old.values.length != values.length ||
      (values.isNotEmpty &&
          old.values.isNotEmpty &&
          old.values.last != values.last);
}
