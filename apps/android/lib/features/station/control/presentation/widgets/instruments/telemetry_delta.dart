import 'package:flutter/material.dart';

/// Change in a reading since the previous sample.
///
/// Deliberately neutral in colour. A rising depth is not "good" and a falling
/// speed is not "bad"; colouring them would assert a judgement the dashboard
/// has no basis for.
class TelemetryDelta extends StatelessWidget {
  const TelemetryDelta({
    super.key,
    required this.value,
    required this.unit,
    this.fractionDigits = 1,
  });
  final double value;
  final String unit;
  final int fractionDigits;

  @override
  Widget build(BuildContext context) {
    final magnitude = value.abs();
    final text = magnitude.toStringAsFixed(fractionDigits);
    // Nothing moved worth reporting at this precision; an arrow beside "0.0"
    // claims a direction the number does not support.
    if (double.parse(text) == 0) return const SizedBox.shrink();

    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    final rising = value > 0;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: colors.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            rising ? Icons.arrow_upward : Icons.arrow_downward,
            size: 12,
            color: colors.onSurfaceVariant,
          ),
          const SizedBox(width: 3),
          Text(
            '$text $unit',
            style: theme.textTheme.labelSmall?.copyWith(
              fontWeight: FontWeight.w700,
              color: colors.onSurfaceVariant,
              fontFeatures: const [FontFeature.tabularFigures()],
            ),
          ),
        ],
      ),
    );
  }
}
