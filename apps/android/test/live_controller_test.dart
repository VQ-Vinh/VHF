import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/features/live/live_controller.dart';
import 'package:prana_mobile/models/station.dart';

void main() {
  StationModel station({
    bool running = false,
    int desiredGeneration = 1,
    int observedGeneration = 1,
    String language = 'en',
    String? lastError,
  }) => StationModel(
    id: 'station-1',
    name: 'Station',
    platform: 'windows',
    active: true,
    captureState: running ? 'listening' : 'idle',
    desired: DesiredState(
      running: running,
      targetLanguage: language,
      retryGeneration: 0,
      generation: desiredGeneration,
    ),
    observedGeneration: observedGeneration,
    sessionId: 'session-1',
    sequence: 1,
    lastSeenAt: DateTime.now(),
    lastError: lastError,
  );

  test(
    'command remains pending until observed generation catches up',
    () async {
      final controller = LiveUxController(
        stationId: 'station-1',
        send: ({running, targetLanguage, retry = false}) async {},
      );
      final initial = station();

      await controller.setRunning(initial, true);
      expect(controller.state.phase, LiveCommandPhase.awaitingStation);
      expect(controller.state.pendingRunning, isTrue);

      controller.synchronize(
        station(desiredGeneration: 2, observedGeneration: 1, running: true),
        online: true,
      );
      expect(controller.state.phase, LiveCommandPhase.awaitingStation);

      controller.synchronize(
        station(desiredGeneration: 2, observedGeneration: 2, running: true),
        online: true,
      );
      expect(controller.state.phase, LiveCommandPhase.applied);
      expect(controller.state.pendingRunning, isNull);
    },
  );

  test('stop command exposes its pending direction', () async {
    final controller = LiveUxController(
      stationId: 'station-1',
      send: ({running, targetLanguage, retry = false}) async {},
    );

    await controller.setRunning(station(running: true), false);

    expect(controller.state.phase, LiveCommandPhase.awaitingStation);
    expect(controller.state.pendingRunning, isFalse);
  });

  test('language rolls back when API request fails', () async {
    final controller = LiveUxController(
      stationId: 'station-1',
      send: ({running, targetLanguage, retry = false}) async {
        throw Exception('network');
      },
    );

    await controller.setLanguage(station(language: 'en'), 'vi');

    expect(controller.state.phase, LiveCommandPhase.failed);
    expect(controller.state.optimisticLanguage, 'en');
    expect(controller.state.error, contains('network'));
  });

  test('offline state is reflected in the UX controller', () {
    final controller = LiveUxController(
      stationId: 'station-1',
      send: ({running, targetLanguage, retry = false}) async {},
    );

    controller.synchronize(station(), online: false);

    expect(controller.state.phase, LiveCommandPhase.offline);
  });

  test('audio processing errors do not become command failures', () {
    final controller = LiveUxController(
      stationId: 'station-1',
      send: ({running, targetLanguage, retry = false}) async {},
    );

    controller.synchronize(
      station(lastError: 'RATE_LIMITED: busy'),
      online: true,
    );

    expect(controller.state.phase, LiveCommandPhase.idle);
    expect(controller.state.error, isNull);
  });
}
