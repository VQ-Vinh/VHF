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

/// The chart with the fix on it: coordinates, heading, when it was taken and
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
    final readout =
        fix == null
            ? null
            : _Coordinates(
              latitude: formatDms(fix.latitude, positive: 'N', negative: 'S'),
              longitude: formatDms(fix.longitude, positive: 'E', negative: 'W'),
            );
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
              LayoutBuilder(
                builder: (context, constraints) {
                  // Over the chart while there is room for the readout and the
                  // rose without covering the vessel; under a large text scale
                  // the readout drops below the chart instead of swallowing it.
                  final overlay =
                      readout != null &&
                      constraints.maxWidth >=
                          MediaQuery.textScalerOf(context).scale(260);
                  final chart = MapWidget(
                    position: position,
                    heading: heading,
                    track: track,
                  );
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Stack(
                        children: [
                          chart,
                          if (overlay)
                            PositionedDirectional(
                              top: 8,
                              start: 8,
                              child: ConstrainedBox(
                                constraints: BoxConstraints(
                                  maxWidth: constraints.maxWidth * .5,
                                ),
                                child: readout,
                              ),
                            ),
                          if (heading != null)
                            PositionedDirectional(
                              top: 8,
                              end: 8,
                              child: DecoratedBox(
                                decoration: BoxDecoration(
                                  color: palette.surface.withValues(alpha: .86),
                                  shape: BoxShape.circle,
                                ),
                                child: CompassRose(degrees: heading, size: 58),
                              ),
                            ),
                        ],
                      ),
                      if (readout != null && !overlay) ...[
                        const SizedBox(height: 10),
                        readout,
                      ],
                    ],
                  );
                },
              ),
              const SizedBox(height: 12),
              AdaptiveFields(
                minimumWidth: 120,
                children: [
                  _Field(
                    label: 'FIX',
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
    return Container(
      key: const ValueKey('gps-coordinates'),
      padding: const EdgeInsets.fromLTRB(10, 8, 10, 9),
      decoration: BoxDecoration(
        color: colors.surface.withValues(alpha: .86),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: colors.outlineVariant),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.place_outlined, size: 12, color: colors.primary),
              const SizedBox(width: 4),
              Flexible(
                child: Text(
                  'GPS',
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
          Text(latitude, style: style),
          Text(longitude, style: style),
        ],
      ),
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
