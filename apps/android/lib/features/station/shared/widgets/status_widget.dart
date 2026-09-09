import 'package:prana_mobile/features/station/shared/widgets/telemetry_label.dart';
import 'package:prana_mobile/l10n/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../application/station_telemetry_controller.dart';

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
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        AppLocalizations.of(context).dashboardStatus,
        style: Theme.of(context).textTheme.titleMedium,
      ),
      const SizedBox(height: 12),
      Text(
        (online
            ? AppLocalizations.of(context).stationOnline
            : AppLocalizations.of(context).stationOffline),
      ),
      const SizedBox(height: 8),
      Text(telemetryLabel(AppLocalizations.of(context), freshness)),
      if (timestamp != null)
        Text(DateFormat.Hms().format(timestamp!.toLocal())),
      if (freshness == TelemetryFreshness.error)
        TextButton(
          onPressed: onRetry,
          child: Text(AppLocalizations.of(context).retry),
        ),
    ],
  );
}
