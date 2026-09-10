import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:prana_mobile/core/responsive.dart';
import 'package:prana_mobile/core/surfaces.dart';
import 'package:prana_mobile/l10n/app_localizations.dart';
import 'package:prana_mobile/telemetry/domain/telemetry_repository.dart';

/// Latitude, longitude and fix time as one instrument strip.
///
/// The hemisphere letters come from the sign rather than being printed with a
/// minus sign, because that is how a position is read aloud on the bridge.
/// [AdaptiveFields] stacks the three when the text scale no longer leaves room
/// for a row, so nothing has to shrink.
class PositionWidget extends StatelessWidget {
  const PositionWidget({
    super.key,
    required this.position,
    this.timestamp,
    this.showSource = true,
  });
  final TelemetryPosition? position;
  final DateTime? timestamp;
  final bool showSource;

  static String _degrees(double value, String positive, String negative) =>
      '${value.abs().toStringAsFixed(5)}°  ${value < 0 ? negative : positive}';

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: panelDecoration(context),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Semantics(
            label:
                '${l10n.position}: '
                '${position?.latitude ?? '—'}, ${position?.longitude ?? '—'}',
            excludeSemantics: true,
            child: AdaptiveFields(
              minimumWidth: 88,
              gap: 12,
              children: [
                _Field(
                  icon: Icons.place_outlined,
                  label: 'LAT',
                  value:
                      position == null
                          ? '—'
                          : _degrees(position!.latitude, 'N', 'S'),
                ),
                _Field(
                  label: 'LON',
                  value:
                      position == null
                          ? '—'
                          : _degrees(position!.longitude, 'E', 'W'),
                ),
                _Field(
                  label: 'FIX',
                  value:
                      timestamp == null
                          ? '—'
                          : DateFormat.Hms().format(timestamp!.toLocal()),
                ),
              ],
            ),
          ),
          if (showSource) ...[
            const SizedBox(height: 10),
            Text(
              l10n.telemetryMock,
              style: theme.textTheme.bodySmall?.copyWith(
                color: colors.onSurfaceVariant,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _Field extends StatelessWidget {
  const _Field({required this.label, required this.value, this.icon});
  final String label, value;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (icon != null) ...[
              Icon(icon, size: 13, color: colors.primary),
              const SizedBox(width: 5),
            ],
            Flexible(
              child: Text(
                label,
                style: theme.textTheme.labelSmall?.copyWith(
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.8,
                  color: colors.onSurfaceVariant,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 3),
        Text(
          value,
          style: theme.textTheme.titleSmall?.copyWith(
            fontWeight: FontWeight.w700,
            color: colors.onSurface,
            fontFeatures: const [FontFeature.tabularFigures()],
          ),
        ),
      ],
    );
  }
}
