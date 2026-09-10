import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:prana_mobile/app/di/telemetry_providers.dart';
import 'widgets/speed_widget.dart';
import 'widgets/depth_widget.dart';
import 'widgets/heading_widget.dart';
import '../../shared/widgets/status_widget.dart';

class DashboardTab extends ConsumerWidget {
  const DashboardTab({
    super.key,
    required this.stationId,
    required this.stationOnline,
  });
  final String stationId;
  final bool stationOnline;

  static const double _gutter = 14;
  static const double _margin = 16;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final controller = ref.watch(stationTelemetryControllerProvider(stationId));
    final state = controller.state;
    final sample = state.snapshot;
    final instruments = <Widget>[
      SpeedWidget(
        value: sample?.speedKnots,
        delta: state.speedDelta,
        history: [for (final entry in state.history) entry.speedKnots],
      ),
      DepthWidget(value: sample?.depthMetres, delta: state.depthDelta),
      HeadingWidget(value: sample?.headingDegrees),
    ];
    return LayoutBuilder(
      builder: (context, constraints) {
        final scale = MediaQuery.textScalerOf(context).scale(1);
        final wide = constraints.maxWidth >= 840 * scale;
        final columns =
            wide
                ? 3
                : constraints.maxWidth < 360 * scale
                ? 1
                : 2;
        final available = constraints.maxWidth - _margin * 2;
        final width = (available - (columns - 1) * _gutter) / columns;
        return SingleChildScrollView(
          key: const PageStorageKey('dashboard-scroll'),
          padding: const EdgeInsets.fromLTRB(
            _margin,
            _margin,
            _margin,
            _margin + 8,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Wrap(
                spacing: _gutter,
                runSpacing: _gutter,
                children: [
                  for (var i = 0; i < instruments.length; i++)
                    SizedBox(
                      // Heading carries the compass, so it takes the whole row
                      // rather than sharing one with a reading half its height.
                      width:
                          !wide && columns == 2 && i == 2 ? available : width,
                      child: instruments[i],
                    ),
                ],
              ),
              const SizedBox(height: 28),
              StatusWidget(
                online: stationOnline,
                freshness: state.freshness,
                timestamp: sample?.timestamp,
                onRetry: controller.retry,
              ),
            ],
          ),
        );
      },
    );
  }
}
