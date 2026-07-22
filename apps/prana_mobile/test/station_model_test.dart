import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/models/station.dart';

void main() {
  test('desired state decodes command generations', () {
    final state = DesiredState.fromMap({
      'running': true,
      'target_language': 'vi',
      'retry_generation': 3,
      'generation': 7,
    });
    expect(state.running, isTrue);
    expect(state.targetLanguage, 'vi');
    expect(state.retryGeneration, 3);
    expect(state.generation, 7);
  });

  test('station becomes offline after heartbeat threshold', () {
    final heartbeat = DateTime.utc(2026, 7, 22, 12);
    final station = StationModel(
      id: 'station',
      name: 'Bridge',
      platform: 'Linux',
      active: true,
      captureState: 'listening',
      desired: const DesiredState(
        running: true,
        targetLanguage: 'vi',
        retryGeneration: 0,
        generation: 1,
      ),
      observedGeneration: 1,
      sessionId: 'session',
      sequence: 2,
      lastSeenAt: heartbeat,
    );
    expect(
      station.isOnlineAt(heartbeat.add(const Duration(seconds: 15))),
      isTrue,
    );
    expect(
      station.isOnlineAt(heartbeat.add(const Duration(seconds: 16))),
      isFalse,
    );
  });
}
