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

  test('station capabilities decode the capability hash', () {
    final capabilities = StationCapabilities.fromMap({
      'capability_hash': 'new-hash',
      'capture_modes': ['device'],
      'audio_devices': <Map<String, dynamic>>[],
      'storage_path': r'C:\PRANA',
    });

    expect(capabilities.capabilityHash, 'new-hash');
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

  test('translation results sort by time with stable tie breakers', () {
    TranslationResult result(String id, int sequence, DateTime timestamp) =>
        TranslationResult(
          requestId: id,
          sequence: sequence,
          transcript: id,
          translation: id,
          language: 'en',
          confidence: 1,
          timestamp: timestamp,
        );

    final sameTime = DateTime.utc(2026, 7, 23, 10);
    final values = [
      result('new', 3, sameTime.add(const Duration(seconds: 2))),
      result('second', 2, sameTime),
      result('first', 1, sameTime),
    ]..sort(compareTranslationChronologically);

    expect(values.map((item) => item.requestId), ['first', 'second', 'new']);
  });

  test('translation result decodes its target speech language', () {
    final value = TranslationResult.fromMap({
      'request_id': 'request-1',
      'sequence': 1,
      'translation': 'Xin chào',
      'target_language': 'vi',
      'timestamp': '2026-07-28T12:00:00Z',
    });

    expect(value.targetLanguage, 'vi');
  });
}
