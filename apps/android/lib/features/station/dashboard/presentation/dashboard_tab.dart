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
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final controller = ref.watch(stationTelemetryControllerProvider(stationId));
    final state = controller.state;
    final sample = state.snapshot;
    final instruments = <Widget>[
      SpeedWidget(value: sample?.speedKnots),
      DepthWidget(value: sample?.depthMetres),
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
        final width =
            (constraints.maxWidth - 32 - (columns - 1) * 12) / columns;
        return SingleChildScrollView(
          key: const PageStorageKey('dashboard-scroll'),
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: [
                  for (var i = 0; i < instruments.length; i++)
                    SizedBox(
                      width:
                          !wide && columns == 2 && i == 2
                              ? constraints.maxWidth - 32
                              : width,
                      child: instruments[i],
                    ),
                ],
              ),
              const SizedBox(height: 24),
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
