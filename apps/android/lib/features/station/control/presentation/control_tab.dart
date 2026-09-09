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
        const SizedBox(height: 16),
        SteeringWheel(
          state: steering,
          active: widget.active,
          onChanged: () => setState(() {}),
        ),
      ],
    );
    final map = Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(telemetryLabel(AppLocalizations.of(context), state.freshness)),
        if (sample != null)
          Text(DateFormat.Hms().format(sample.timestamp.toLocal())),
        if (state.freshness == TelemetryFreshness.error)
          TextButton(
            onPressed: controller.retry,
            child: Text(AppLocalizations.of(context).retry),
          ),
        MapWidget(position: sample?.position, heading: sample?.headingDegrees),
      ],
    );
    return Column(
      children: [
        Padding(
          key: const ValueKey('control-position'),
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: PositionWidget(position: sample?.position, showSource: false),
        ),
        Expanded(
          child: LayoutBuilder(
            builder: (context, constraints) {
              final wide =
                  constraints.maxWidth >=
                  MediaQuery.textScalerOf(context).scale(840);
              return SingleChildScrollView(
                key: const PageStorageKey('control-scroll'),
                padding: const EdgeInsets.all(16),
                child:
                    wide
                        ? Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Expanded(flex: 2, child: map),
                            const SizedBox(width: 24),
                            Expanded(child: controls),
                          ],
                        )
                        : Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [map, const SizedBox(height: 24), controls],
                        ),
              );
            },
          ),
        ),
      ],
    );
  }
}
