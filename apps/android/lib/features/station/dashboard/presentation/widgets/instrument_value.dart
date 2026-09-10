import 'package:flutter/material.dart';
import 'package:prana_mobile/core/surfaces.dart';

/// One telemetry instrument: a labelled reading with an optional trend graphic.
///
/// The reading keeps its scale-down fitting so a long value at text scale 2.0
/// shrinks inside the card instead of overflowing it, which is the exception
/// docs/architecture/responsive-ui-audit.md records for numeric instruments.
class InstrumentValue extends StatelessWidget {
  const InstrumentValue({
    super.key,
    required this.label,
    required this.icon,
    required this.value,
    required this.unit,
    this.delta,
    this.visual,
    this.trailing,
  });
  final String label, value, unit;
  final IconData icon;

  /// Sits beside the unit. Null when the reading has nothing to compare to.
  final Widget? delta;

  /// Trend or scale drawing below the reading.
  final Widget? visual;

  /// Graphic that sits beside the reading when the card is wide enough for
  /// both, and drops below it when it is not. The compass uses this: pinned
  /// under the number it left a tall void beside a short line of digits.
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    return Semantics(
      label: '$label: $value $unit',
      excludeSemantics: true,
      child: Container(
        padding: const EdgeInsets.all(18),
        decoration: panelDecoration(context),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                ExcludeSemantics(
                  child: Container(
                    padding: const EdgeInsets.all(6),
                    decoration: BoxDecoration(
                      color: colors.primary.withValues(alpha: 0.10),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Icon(icon, color: colors.primary, size: 18),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(child: Text(label, style: panelLabelStyle(context))),
              ],
            ),
            const SizedBox(height: 14),
            LayoutBuilder(
              builder: (context, constraints) {
                final reading = Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    FittedBox(
                      fit: BoxFit.scaleDown,
                      alignment: Alignment.centerLeft,
                      child: Text(
                        value,
                        style: TextStyle(
                          fontSize: 46,
                          height: 1.05,
                          fontWeight: FontWeight.w700,
                          letterSpacing: -1,
                          color: colors.onSurface,
                          fontFeatures: const [FontFeature.tabularFigures()],
                        ),
                      ),
                    ),
                    const SizedBox(height: 2),
                    // Unit and trend share a line so the card keeps its rhythm
                    // whether or not a delta exists; both wrap rather than clip.
                    Wrap(
                      crossAxisAlignment: WrapCrossAlignment.center,
                      spacing: 10,
                      runSpacing: 4,
                      children: [
                        Text(
                          unit,
                          style: theme.textTheme.labelLarge?.copyWith(
                            fontWeight: FontWeight.w600,
                            letterSpacing: 0.4,
                            color: colors.onSurfaceVariant,
                          ),
                        ),
                        if (delta != null) delta!,
                      ],
                    ),
                  ],
                );
                if (trailing == null) return reading;
                // Below the threshold the digits would be squeezed harder than
                // the saved height is worth, so the graphic drops under them.
                if (constraints.maxWidth < 240) {
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      reading,
                      const SizedBox(height: 16),
                      Center(child: trailing!),
                    ],
                  );
                }
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Expanded(child: reading),
                    const SizedBox(width: 16),
                    trailing!,
                  ],
                );
              },
            ),
            if (visual != null) ...[const SizedBox(height: 16), visual!],
          ],
        ),
      ),
    );
  }
}
