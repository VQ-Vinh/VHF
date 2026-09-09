import 'package:prana_mobile/domain/station/station.dart';
import 'dart:async';
import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/runtime/station/station_session.dart';
import 'package:prana_mobile/runtime/vhf/live_controller.dart';
import 'package:prana_mobile/runtime/vhf/tx_controller.dart';
import 'support/test_recorder.dart';
import 'package:prana_mobile/domain/radio/tx/tx_phase.dart';
import 'support/fake_tx_repository.dart';

void main() {
  test(
    'tab departure ends HTT once and preserves review without confirming',
    () async {
      final recorder = TestRecorder()..startGate = Completer<void>();
      final tx = TxController(
        stationId: 's',
        repository: FakeTxRepository(processingDelay: Duration.zero),
        recorder: recorder,
      );
      final session = StationSession(
        uid: 'u',
        stationId: 's',
        rx: LiveUxController(
          stationId: 's',
          send: ({running, targetLanguage, retry = false}) async {},
        ),
        tx: tx,
      );
      tx.setStationAvailability(
        online: true,
        running: true,
        commandPending: false,
      );
      tx.startRecording();
      final release = tx.stopRecording();
      await tx.stopRecording();
      expect(tx.state.phase, TxPhase.processing);
      recorder.startGate!.complete();
      await Future<void>.delayed(Duration.zero);
      await release;
      expect(recorder.stops, 1);
      expect(tx.state.phase, TxPhase.reviewReady);
      expect(tx.state.draft, isNotNull);
      expect(recorder.disposals, 0);
      session.dispose();
      expect(recorder.disposals, 1);
    },
  );

  test(
    'disposed recording completion cannot upload or notify a new session',
    () async {
      final recorder = TestRecorder()..startGate = Completer<void>();
      final tx = TxController(
        stationId: 's',
        repository: FakeTxRepository(processingDelay: Duration.zero),
        recorder: recorder,
      );
      tx.setStationAvailability(
        online: true,
        running: true,
        commandPending: false,
      );
      tx.startRecording();
      final stopping = tx.stopRecording();
      tx.dispose();
      recorder.startGate!.complete();
      await stopping;
      expect(recorder.stops, 0);
      expect(recorder.disposals, 1);
    },
  );
  test(
    'background cancellation blocks a concurrent tab release during mic startup',
    () async {
      final recorder = TestRecorder()..startGate = Completer<void>();
      final tx = TxController(
        stationId: 's',
        repository: FakeTxRepository(processingDelay: Duration.zero),
        recorder: recorder,
      );
      tx.setStationAvailability(
        online: true,
        running: true,
        commandPending: false,
      );
      tx.startRecording();
      final cancelling = tx.cancelRecordingForBackground();
      await tx.stopRecording();
      tx.startRecording();
      expect(recorder.starts, 1);
      recorder.startGate!.complete();
      await cancelling;
      expect(recorder.stops, 0);
      expect(recorder.cancels, 1);
      expect(tx.state.phase, TxPhase.idle);
      tx.dispose();
    },
  );

  test('RX command completion after session disposal is ignored', () async {
    final pending = Completer<void>();
    final rx = LiveUxController(
      stationId: 's',
      send: ({running, targetLanguage, retry = false}) => pending.future,
    );
    final station = StationModel(
      id: 's',
      name: 's',
      platform: 'linux',
      active: true,
      captureState: 'idle',
      observedGeneration: 0,
      sessionId: '',
      sequence: 0,
      lastSeenAt: null,
      desired: const DesiredState(
        running: false,
        targetLanguage: 'vi',
        retryGeneration: 0,
        generation: 0,
      ),
    );
    var notifications = 0;
    rx.addListener(() => notifications++);
    final request = rx.retry(station);
    rx.dispose();
    final before = notifications;
    pending.complete();
    await request;
    expect(notifications, before);
  });
}
