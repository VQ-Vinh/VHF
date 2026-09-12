import 'package:flutter/material.dart';
import 'package:prana_mobile/core/surfaces.dart';

/// One reading in the instrument strip above the chart.
///
/// The number keeps its scale-down fitting so a long value at text scale 2.0
/// shrinks inside its cell instead of overflowing it, which is the exception
/// docs/architecture/responsive-ui-audit.md records for numeric instruments.
class InstrumentValue extends StatelessWidget {
  const InstrumentValue({
    super.key,
    required this.label,
    required this.icon,
    required this.value,
    required this.unit,
    this.extra,
    this.visual,
  });
  final String label, value, unit;
  final IconData icon;

  /// A chip under the reading: the change since the last sample, or the
  /// compass point for a heading. Null when there is nothing to add.
  final Widget? extra;

  /// A scale or bar under the reading, such as the depth track.
  final Widget? visual;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    return Semantics(
      label: '$label: $value $unit',
      excludeSemantics: true,
      child: Container(
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 12),
        decoration: panelDecoration(context),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              children: [
                ExcludeSemantics(
                  child: Icon(icon, color: colors.primary, size: 14),
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    label,
                    style: theme.textTheme.labelSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.6,
                      color: colors.onSurfaceVariant,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            // Number and unit on one line: in a strip cell a unit on its own
            // row costs a whole line for two letters.
            Row(
              crossAxisAlignment: CrossAxisAlignment.baseline,
              textBaseline: TextBaseline.alphabetic,
              children: [
                Flexible(
                  child: FittedBox(
                    fit: BoxFit.scaleDown,
                    alignment: Alignment.centerLeft,
                    child: Text(
                      value,
                      style: TextStyle(
                        fontSize: 28,
                        height: 1.05,
                        fontWeight: FontWeight.w700,
                        letterSpacing: -0.5,
                        color: colors.onSurface,
                        fontFeatures: const [FontFeature.tabularFigures()],
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 4),
                Flexible(
                  child: Text(
                    unit,
                    style: theme.textTheme.labelMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                      letterSpacing: 0.4,
                      color: colors.onSurfaceVariant,
                    ),
                  ),
                ),
              ],
            ),
            if (extra != null) ...[const SizedBox(height: 6), extra!],
            if (visual != null) ...[const SizedBox(height: 8), visual!],
          ],
        ),
      ),
    );
  }
}

/// A small neutral pill under a reading.
class InstrumentChip extends StatelessWidget {
  const InstrumentChip({super.key, required this.label});
  final String label;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
      decoration: BoxDecoration(
        color: colors.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        label,
        style: theme.textTheme.labelSmall?.copyWith(
          fontWeight: FontWeight.w800,
          letterSpacing: 0.5,
          color: colors.onSurfaceVariant,
        ),
      ),
    );
  }
}
