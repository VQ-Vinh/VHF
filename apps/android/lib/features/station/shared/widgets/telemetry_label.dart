import 'package:prana_mobile/features/station/shared/application/station_telemetry_controller.dart';
import 'package:prana_mobile/l10n/app_localizations.dart';

String telemetryLabel(AppLocalizations l10n, TelemetryFreshness freshness) =>
    switch (freshness) {
      TelemetryFreshness.missing => l10n.telemetryMissing,
      TelemetryFreshness.fresh => l10n.telemetryFresh,
      TelemetryFreshness.stale => l10n.telemetryStale,
      TelemetryFreshness.error => l10n.telemetryError,
    };
