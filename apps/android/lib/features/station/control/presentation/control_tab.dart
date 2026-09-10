import 'package:prana_mobile/features/station/shared/widgets/telemetry_label.dart';
import 'package:prana_mobile/l10n/app_localizations.dart';
import 'package:intl/intl.dart';
import '../../shared/application/station_telemetry_controller.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:prana_mobile/app/di/telemetry_providers.dart';
import '../application/steering_state.dart';
import 'widgets/control_widget.dart';
import 'widgets/map_widget.dart';
import 'widgets/position_widget.dart';
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
    final map = MapWidget(
      position: sample?.position,
      heading: sample?.headingDegrees,
      track: [for (final entry in state.history) entry.position],
    );
    return Column(
      // Stretch, or the position strip shrinks to its own text and floats in
      // the middle of the screen while the cards below run edge to edge.
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          key: const ValueKey('control-position'),
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
          child: PositionWidget(
            position: sample?.position,
            timestamp: sample?.timestamp,
            showSource: false,
          ),
        ),
        Expanded(
          child: LayoutBuilder(
            builder: (context, constraints) {
              final wide =
                  constraints.maxWidth >=
                  MediaQuery.textScalerOf(context).scale(840);
              return SingleChildScrollView(
                key: const PageStorageKey('control-scroll'),
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    if (wide)
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(flex: 2, child: map),
                          const SizedBox(width: 24),
                          Expanded(child: controls),
                        ],
                      )
                    else ...[
                      map,
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
            },
          ),
        ),
      ],
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
