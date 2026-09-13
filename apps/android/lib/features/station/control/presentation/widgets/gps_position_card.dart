import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:prana_mobile/core/responsive.dart';
import 'package:prana_mobile/core/surfaces.dart';
import 'package:prana_mobile/l10n/app_localizations.dart';
import 'package:prana_mobile/telemetry/domain/telemetry_repository.dart';

import 'coordinates.dart';
import 'instruments/compass_rose.dart';
import 'map_widget.dart';
import 'sim_notice.dart';

/// The chart with coordinates above it, heading, when it was taken and
/// where it came from.
class GpsPositionCard extends StatelessWidget {
  const GpsPositionCard({
    super.key,
    required this.position,
    required this.heading,
    required this.timestamp,
    required this.source,
    this.track = const [],
  });

  final TelemetryPosition? position;
  final double? heading;
  final DateTime? timestamp;
  final TelemetrySource? source;

  /// Recent fixes, oldest first. Drawn as the track behind the vessel.
  final List<TelemetryPosition> track;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = Theme.of(context).colorScheme;
    final fix = position;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 10),
          child: Text(l10n.gpsPosition, style: panelLabelStyle(context)),
        ),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: panelDecoration(context),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _Coordinates(
                latitude:
                    fix == null
                        ? '—'
                        : formatDms(fix.latitude, positive: 'N', negative: 'S'),
                longitude:
                    fix == null
                        ? '—'
                        : formatDms(
                          fix.longitude,
                          positive: 'E',
                          negative: 'W',
                        ),
              ),
              const SizedBox(height: 10),
              Stack(
                children: [
                  MapWidget(position: position, heading: heading, track: track),
                  if (heading != null)
                    PositionedDirectional(
                      top: 8,
                      end: 8,
                      child: DecoratedBox(
                        decoration: BoxDecoration(
                          color: palette.surface.withValues(alpha: .86),
                          shape: BoxShape.circle,
                        ),
                        child: CompassRose(degrees: heading, size: 48),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 12),
              AdaptiveFields(
                minimumWidth: 120,
                children: [
                  _Field(
                    label: l10n.telemetryUpdatedAt,
                    value:
                        timestamp == null
                            ? '—'
                            : DateFormat.Hms().format(timestamp!.toLocal()),
                  ),
                  _Field(
                    key: const ValueKey('gps-source'),
                    label: l10n.source,
                    // The readings are generated on the phone. Naming a real
                    // receiver here would be the one lie a navigator cannot
                    // check from the screen.
                    value:
                        source == null
                            ? '—'
                            : l10n.sourceSimulated.toUpperCase(),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              SimNotice(
                icon: Icons.warning_amber_rounded,
                message: l10n.mapMockNotice,
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _Coordinates extends StatelessWidget {
  const _Coordinates({required this.latitude, required this.longitude});
  final String latitude, longitude;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    final style = theme.textTheme.titleSmall?.copyWith(
      fontWeight: FontWeight.w700,
      color: colors.onSurface,
      fontFeatures: const [FontFeature.tabularFigures()],
    );
    return Wrap(
      key: const ValueKey('gps-coordinates'),
      spacing: 16,
      runSpacing: 4,
      children: [Text(latitude, style: style), Text(longitude, style: style)],
    );
  }
}

class _Field extends StatelessWidget {
  const _Field({super.key, required this.label, required this.value});
  final String label, value;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          label.toUpperCase(),
          style: theme.textTheme.labelSmall?.copyWith(
            fontWeight: FontWeight.w700,
            letterSpacing: 0.8,
            color: colors.onSurfaceVariant,
          ),
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
