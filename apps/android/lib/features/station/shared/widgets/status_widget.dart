import 'package:prana_mobile/core/surfaces.dart';
import 'package:prana_mobile/core/widgets.dart';
import 'package:prana_mobile/features/station/shared/widgets/telemetry_label.dart';
import 'package:prana_mobile/l10n/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../application/station_telemetry_controller.dart';

/// Connection and telemetry state, as one scannable panel.
///
/// The freshness strings already open with "Simulated telemetry", so the
/// source is disclosed once here rather than repeated on a row of its own.
/// Nothing on this panel claims a real instrument feed, because there is none.
class StatusWidget extends StatelessWidget {
  const StatusWidget({
    super.key,
    required this.online,
    required this.freshness,
    required this.timestamp,
    required this.onRetry,
  });
  final bool online;
  final TelemetryFreshness freshness;
  final DateTime? timestamp;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 10),
          child: Text(l10n.dashboardStatus, style: panelLabelStyle(context)),
        ),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(16),
          decoration: panelDecoration(context),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Pill and clock wrap instead of colliding when the locale is
              // long or the text scale is large.
              Wrap(
                crossAxisAlignment: WrapCrossAlignment.center,
                alignment: WrapAlignment.spaceBetween,
                spacing: 12,
                runSpacing: 8,
                children: [
                  StatusPill(
                    label: online ? l10n.stationOnline : l10n.stationOffline,
                    online: online,
                  ),
                  if (timestamp != null)
                    Text(
                      DateFormat.Hms().format(timestamp!.toLocal()),
                      style: theme.textTheme.labelMedium?.copyWith(
                        color: colors.onSurfaceVariant,
                        fontFeatures: const [FontFeature.tabularFigures()],
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 12),
              Divider(height: 1, thickness: 1, color: colors.outlineVariant),
              const SizedBox(height: 12),
              Text(
                telemetryLabel(l10n, freshness),
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: colors.onSurfaceVariant,
                ),
              ),
              if (freshness == TelemetryFreshness.error) ...[
                const SizedBox(height: 4),
                Align(
                  alignment: AlignmentDirectional.centerStart,
                  child: TextButton(
                    onPressed: onRetry,
                    child: Text(l10n.retry),
                  ),
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }
}
