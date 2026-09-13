import 'package:flutter/material.dart';
import 'package:prana_mobile/core/surfaces.dart';

/// One reading in the instrument strip above the chart.
///
/// Values and units wrap naturally; the strip reflows at large text scales.
class InstrumentValue extends StatelessWidget {
  const InstrumentValue({
    super.key,
    required this.label,
    required this.icon,
    required this.value,
    required this.unit,
    this.superscriptUnit = false,
    this.qualifier,
    this.extra,
    this.visual,
  });
  final String label, value, unit;
  final bool superscriptUnit;
  final IconData icon;
  final String? qualifier;

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
      label: '$label: $value $unit${qualifier == null ? '' : ', $qualifier'}',
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
                  child: Wrap(
                    spacing: 4,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      Text(
                        label,
                        style: theme.textTheme.labelSmall?.copyWith(
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.6,
                          color: colors.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Row(
              crossAxisAlignment: CrossAxisAlignment.baseline,
              textBaseline: TextBaseline.alphabetic,
              children: [
                Flexible(
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
                SizedBox(width: superscriptUnit ? 0 : 4),
                Text(
                  unit,
                  style: theme.textTheme.labelMedium?.copyWith(
                    fontSize: superscriptUnit ? 28 : null,
                    height: superscriptUnit ? 1.05 : null,
                    fontWeight: FontWeight.w600,
                    color:
                        superscriptUnit
                            ? colors.onSurface
                            : colors.onSurfaceVariant,
                  ),
                ),
                if (qualifier != null) ...[
                  const SizedBox(width: 4),
                  Text(
                    qualifier!,
                    style: theme.textTheme.labelMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                      color: colors.onSurfaceVariant,
                    ),
                  ),
                ],
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
