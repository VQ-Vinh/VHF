import 'package:prana_mobile/app/di/radio_providers.dart';
import 'package:prana_mobile/runtime/station/station_session.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/legacy.dart';
import 'package:prana_mobile/telemetry/domain/telemetry_repository.dart';
import 'package:prana_mobile/telemetry/data/mock_telemetry_repository.dart';
import 'package:prana_mobile/features/station/shared/application/station_telemetry_controller.dart';

final telemetryRepositoryProvider = Provider<TelemetryRepository>(
  (ref) => MockTelemetryRepository(),
);
final stationTelemetryControllerProvider = ChangeNotifierProvider.autoDispose
    .family<StationTelemetryController, String>(
      (ref, stationId) => StationTelemetryController(
        ref.watch(telemetryRepositoryProvider),
        stationId,
      ),
    );

final stationRuntimeStateProvider = Provider.autoDispose
    .family<StationRuntimeState, String>((ref, id) {
      final session = ref.watch(stationSessionProvider(id));
      final telemetry =
          ref.watch(stationTelemetryControllerProvider(id)).state.snapshot;
      return session.state.withTelemetry(telemetry);
    });
