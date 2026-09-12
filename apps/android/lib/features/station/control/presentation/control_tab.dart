import 'package:prana_mobile/features/station/shared/widgets/telemetry_label.dart';
import 'package:prana_mobile/l10n/app_localizations.dart';
import 'package:intl/intl.dart';
import '../../shared/application/station_telemetry_controller.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:prana_mobile/app/di/telemetry_providers.dart';
import '../application/steering_state.dart';
import 'widgets/control_widget.dart';
import 'widgets/gps_position_card.dart';
import 'widgets/instruments/instrument_strip.dart';
import 'widgets/steering_wheel.dart';

class ControlTab extends ConsumerStatefulWidget {
  const ControlTab({super.key, required this.stationId, required this.active});
  final String stationId;
  final bool active;
  @override
  ConsumerState<ControlTab> createState() => _ControlTabState();
}

class _ControlTabState extends ConsumerState<ControlTab> {
  SteeringState steering = SteeringState();
  @override
  void didUpdateWidget(covariant ControlTab oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.stationId != widget.stationId) steering = SteeringState();
    if (!widget.active) steering.endDrag();
  }

  @override
  Widget build(BuildContext context) {
    final controller = ref.watch(
      stationTelemetryControllerProvider(widget.stationId),
    );
    final state = controller.state;
    final sample = state.snapshot;
    final controls = Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        ControlWidget(
          mode: steering.mode,
          onChanged: (mode) => setState(() => steering.selectMode(mode)),
        ),
        const SizedBox(height: 24),
        SteeringWheel(
          state: steering,
          active: widget.active,
          onChanged: () => setState(() {}),
        ),
      ],
    );
    final instruments = InstrumentStrip(
      speedKnots: sample?.speedKnots,
      speedDelta: state.speedDelta,
      depthMetres: sample?.depthMetres,
      headingDegrees: sample?.headingDegrees,
    );
    final chart = GpsPositionCard(
      position: sample?.position,
      heading: sample?.headingDegrees,
      timestamp: sample?.timestamp,
      source: sample?.source,
      track: [for (final entry in state.history) entry.position],
    );
    return LayoutBuilder(
      builder: (context, constraints) {
        final wide =
            constraints.maxWidth >= MediaQuery.textScalerOf(context).scale(840);
        final available = constraints.maxWidth - 32;
        // Pinned above the chart while the readings stay put as the wheel is
        // scrolled to. That needs room in both directions: stacked, or on a
        // short landscape screen at a large text scale, the strip is taller
        // than everything it would leave behind, so it scrolls with the rest.
        // A cell runs about 94dp at text scale 1: caption, number, chip, pad.
        final stripHeight = MediaQuery.textScalerOf(context).scale(94);
        final pinned =
            InstrumentStrip.fitsOneRow(context, available) &&
            (!constraints.hasBoundedHeight ||
                constraints.maxHeight >= stripHeight * 2.6);
        final body = SingleChildScrollView(
          key: const PageStorageKey('control-scroll'),
          padding: EdgeInsets.fromLTRB(16, pinned ? 12 : 16, 16, 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (!pinned) ...[instruments, const SizedBox(height: 20)],
              if (wide)
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(flex: 2, child: chart),
                    const SizedBox(width: 24),
                    Expanded(child: controls),
                  ],
                )
              else ...[
                chart,
                const SizedBox(height: 24),
                controls,
              ],
              const SizedBox(height: 20),
              _TelemetryFooter(
                freshness: state.freshness,
                timestamp: sample?.timestamp,
                onRetry: controller.retry,
              ),
            ],
          ),
        );
        if (!pinned) return body;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              key: const ValueKey('control-instruments'),
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
              child: instruments,
            ),
            Expanded(child: body),
          ],
        );
      },
    );
  }
}

/// Where the readings come from and when they last arrived.
///
/// One line at the foot of the tab rather than three stray Texts above the
/// chart, which is where they used to sit and where they competed with the
/// position for the top of the screen.
class _TelemetryFooter extends StatelessWidget {
  const _TelemetryFooter({
    required this.freshness,
    required this.timestamp,
    required this.onRetry,
  });
  final TelemetryFreshness freshness;
  final DateTime? timestamp;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    final style = theme.textTheme.labelSmall?.copyWith(
      letterSpacing: 0.5,
      color: colors.onSurfaceVariant,
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        Divider(height: 1, thickness: 1, color: colors.outlineVariant),
        const SizedBox(height: 10),
        Wrap(
          alignment: WrapAlignment.spaceBetween,
          crossAxisAlignment: WrapCrossAlignment.center,
          spacing: 12,
          runSpacing: 4,
          children: [
            Text(telemetryLabel(l10n, freshness), style: style),
            if (timestamp != null)
              Text(
                DateFormat.Hms().format(timestamp!.toLocal()),
                style: style?.copyWith(
                  fontFeatures: const [FontFeature.tabularFigures()],
                ),
              ),
          ],
        ),
        if (freshness == TelemetryFreshness.error)
          Align(
            alignment: AlignmentDirectional.centerStart,
            child: TextButton(onPressed: onRetry, child: Text(l10n.retry)),
          ),
      ],
    );
  }
}
