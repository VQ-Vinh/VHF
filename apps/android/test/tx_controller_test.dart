import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/features/tx/application/fake_tx_repository.dart';
import 'package:prana_mobile/features/tx/application/tx_controller.dart';
import 'package:prana_mobile/features/tx/application/tx_repository.dart';
import 'package:prana_mobile/features/tx/domain/tx_draft.dart';
import 'package:prana_mobile/features/tx/domain/tx_failure.dart';
import 'package:prana_mobile/features/tx/domain/tx_phase.dart';

class _OfflineTxRepository implements TxRepository {
  String status = 'transmitting';

  TxDraft get draft => TxDraft(
    id: 'draft-1',
    stationId: 'station-1',
    duration: const Duration(seconds: 1),
    targetLanguage: 'vi',
    transcript: 'Mayday',
    translation: 'Cấp cứu',
    status: status,
    error: status == 'failed' ? 'STATION_OFFLINE_DURING_TX' : null,
  );

  @override
  Future<void> cancelDraft(String draftId) async {}

  @override
  Future<void> confirmTransmission(TxDraft draft, String translation) async {}

  @override
  Future<TxDraft> getDraft(String stationId, String draftId) async => draft;

  @override
  Future<TxDraft> processRecording(TxRecordingInput input) async =>
      draft.copyWith(status: 'review_ready');

  @override
  Future<TxDraft> retryTransmission(TxDraft draft) async =>
      draft.copyWith(status: 'queued');

  @override
  Future<String?> activeDraftId(String stationId) async => null;

  @override
  Future<void> clearActiveDraft(String stationId) async {}
}

class _LostConfirmRepository implements TxRepository {
  int confirmCalls = 0;
  int getCalls = 0;
  int retryCalls = 0;

  TxDraft draft(String status) => TxDraft(
    id: 'draft-1',
    stationId: 'station-1',
    duration: const Duration(seconds: 1),
    targetLanguage: 'vi',
    transcript: 'Mayday',
    translation: 'Nội dung đã sửa',
    status: status,
  );

  @override
  Future<void> cancelDraft(String draftId) async {}

  @override
  Future<void> confirmTransmission(TxDraft draft, String translation) async {
    confirmCalls += 1;
    if (confirmCalls == 1) throw Exception('response lost');
  }

  @override
  Future<TxDraft> getDraft(String stationId, String draftId) async {
    getCalls += 1;
    return draft(
      getCalls == 1
          ? 'review_ready'
          : getCalls == 2
          ? 'transmitting'
          : 'completed',
    );
  }

  @override
  Future<TxDraft> processRecording(TxRecordingInput input) async =>
      draft('review_ready');

  @override
  Future<TxDraft> retryTransmission(TxDraft draft) async {
    retryCalls += 1;
    return this.draft('queued');
  }

  @override
  Future<String?> activeDraftId(String stationId) async => null;

  @override
  Future<void> clearActiveDraft(String stationId) async {}
}

void main() {
  TxController controller({
    Object? processingError,
    Object? transmissionError,
  }) {
    final subject = TxController(
      stationId: 'station-1',
      repository: FakeTxRepository(
        processingDelay: Duration.zero,
        transmissionDelay: Duration.zero,
        processingError: processingError,
        transmissionError: transmissionError,
      ),
      queuePreviewDuration: Duration.zero,
    );
    subject.setStationAvailability(
      online: true,
      running: true,
      commandPending: false,
    );
    return subject;
  }

  test('recording moves through processing and review', () async {
    final subject = controller();
    addTearDown(subject.dispose);

    subject.startRecording();
    expect(subject.state.phase, TxPhase.recording);

    await subject.stopRecording();
    expect(subject.state.phase, TxPhase.reviewReady);
    expect(subject.state.draft, isNotNull);
    expect(subject.state.draft!.targetLanguage, 'vi');
  });

  test('language changes only while idle', () async {
    final subject = controller();
    addTearDown(subject.dispose);

    subject.setTargetLanguage('ja');
    expect(subject.state.targetLanguage, 'ja');

    subject.startRecording();
    subject.setTargetLanguage('en');
    expect(subject.state.targetLanguage, 'ja');
    await subject.cancelDraft();
  });

  test('recording snapshots the configured maximum duration', () async {
    final subject = controller();
    addTearDown(subject.dispose);
    subject.setMaximumDuration(const Duration(seconds: 120));

    subject.startRecording();
    expect(subject.recordingMaximumDuration, const Duration(seconds: 120));

    subject.setMaximumDuration(const Duration(seconds: 5));
    expect(subject.maximumDuration, const Duration(seconds: 5));
    expect(subject.recordingMaximumDuration, const Duration(seconds: 120));

    await subject.stopRecording();
    subject.reset();
    subject.startRecording();
    expect(subject.recordingMaximumDuration, const Duration(seconds: 5));
    await subject.stopRecording();
  });

  test('server recording limit becomes a retryable TX failure', () async {
    final subject = controller(processingError: const TxRecordingTooLong(5));
    addTearDown(subject.dispose);

    subject.startRecording();
    await subject.stopRecording();

    expect(subject.state.phase, TxPhase.failed);
    expect(subject.state.failure, TxFailure.recordingTooLong);
    expect(subject.maximumDuration, const Duration(seconds: 5));
    await subject.retry();
    expect(subject.canStartRecording, isTrue);
  });

  test('confirm cannot be submitted twice', () async {
    final subject = controller();
    addTearDown(subject.dispose);
    subject.startRecording();
    await subject.stopRecording();

    final first = subject.confirmTransmission(subject.state.draft!.translation);
    final second = subject.confirmTransmission(
      subject.state.draft!.translation,
    );
    await Future.wait([first, second]);

    expect(subject.state.phase, TxPhase.completed);
  });

  test('cancel clears an active draft', () async {
    final subject = controller();
    addTearDown(subject.dispose);
    subject.startRecording();
    await subject.stopRecording();

    await subject.cancelDraft();

    expect(subject.state.phase, TxPhase.idle);
    expect(subject.state.draft, isNull);
  });

  test('a completed transmission clears itself without a DONE tap', () async {
    final subject = TxController(
      stationId: 'station-1',
      repository: FakeTxRepository(
        processingDelay: Duration.zero,
        transmissionDelay: Duration.zero,
      ),
      queuePreviewDuration: Duration.zero,
      completedLingerDuration: Duration.zero,
    );
    subject.setStationAvailability(
      online: true,
      running: true,
      commandPending: false,
    );
    addTearDown(subject.dispose);
    subject.startRecording();
    await subject.stopRecording();
    await subject.confirmTransmission('Cấp cứu.');
    expect(subject.state.phase, TxPhase.completed);

    // Let the linger timer fire; nothing else is tapped.
    await Future<void>.delayed(Duration.zero);

    expect(subject.state.phase, TxPhase.idle);
    expect(subject.state.draft, isNull);
  });

  test('a stale linger timer never clears a later recording', () async {
    final subject = TxController(
      stationId: 'station-1',
      repository: FakeTxRepository(
        processingDelay: Duration.zero,
        transmissionDelay: Duration.zero,
      ),
      queuePreviewDuration: Duration.zero,
      completedLingerDuration: const Duration(milliseconds: 60),
    );
    subject.setStationAvailability(
      online: true,
      running: true,
      commandPending: false,
    );
    addTearDown(subject.dispose);
    subject.startRecording();
    await subject.stopRecording();
    await subject.confirmTransmission('Cấp cứu.');
    expect(subject.state.phase, TxPhase.completed);

    // Clearing by hand cancels the pending timer; a recording begun straight
    // after must survive past the moment that timer would have fired.
    subject.reset();
    subject.startRecording();
    await Future<void>.delayed(const Duration(milliseconds: 120));

    expect(subject.state.phase, TxPhase.recording);
  });

  test('confirm sends the edited translation exactly once', () async {
    final repository = FakeTxRepository(
      processingDelay: Duration.zero,
      transmissionDelay: Duration.zero,
    );
    final subject = TxController(
      stationId: 'station-1',
      repository: repository,
      queuePreviewDuration: Duration.zero,
    );
    subject.setStationAvailability(
      online: true,
      running: true,
      commandPending: false,
    );
    addTearDown(subject.dispose);
    subject.startRecording();
    await subject.stopRecording();

    await Future.wait([
      subject.confirmTransmission('Nội dung đã sửa.'),
      subject.confirmTransmission('Không được gửi hai lần.'),
    ]);

    expect(repository.lastConfirmedTranslation, 'Nội dung đã sửa.');
  });

  test('offline station blocks recording', () {
    final subject = controller();
    addTearDown(subject.dispose);

    subject.setStationOnline(false);
    subject.startRecording();

    expect(subject.state.phase, TxPhase.stationOffline);
  });

  test('stopped or command-pending Station blocks recording', () {
    final stopped = controller();
    addTearDown(stopped.dispose);
    stopped.setStationAvailability(
      online: true,
      running: false,
      commandPending: false,
    );
    stopped.startRecording();
    expect(stopped.state.phase, TxPhase.idle);

    final pending = controller();
    addTearDown(pending.dispose);
    pending.setStationAvailability(
      online: true,
      running: true,
      commandPending: true,
    );
    pending.startRecording();
    expect(pending.state.phase, TxPhase.idle);
  });

  test('PTT unavailable blocks TX until Station reports ready', () {
    final subject = controller();

    subject.setStationAvailability(
      online: true,
      running: true,
      commandPending: false,
      pttReady: false,
    );

    expect(subject.state.failure, TxFailure.pttUnavailable);
    expect(subject.canStartRecording, isFalse);
    expect(subject.canRetryTransmission, isFalse);

    subject.setStationAvailability(
      online: true,
      running: true,
      commandPending: false,
      pttReady: true,
    );

    expect(subject.state.phase, TxPhase.idle);
    expect(subject.canStartRecording, isTrue);
  });

  test('processing failure can be reset and retried', () async {
    final subject = controller(processingError: Exception('processing'));
    addTearDown(subject.dispose);
    subject.startRecording();

    await subject.stopRecording();
    expect(subject.state.phase, TxPhase.failed);

    await subject.retry();
    expect(subject.state.phase, TxPhase.idle);
  });

  test(
    'transmission failure only retries after explicit user action',
    () async {
      final subject = controller(transmissionError: Exception('radio'));
      addTearDown(subject.dispose);
      subject.startRecording();
      await subject.stopRecording();

      await subject.confirmTransmission(subject.state.draft!.translation);
      expect(subject.state.phase, TxPhase.failed);

      await subject.retry();
      expect(subject.state.phase, TxPhase.completed);
    },
  );

  test(
    'Station offline exits transmitting UI and waits for server failure',
    () async {
      final repository = _OfflineTxRepository();
      final subject = TxController(
        stationId: 'station-1',
        repository: repository,
        queuePreviewDuration: const Duration(milliseconds: 1),
      );
      subject.setStationAvailability(
        online: true,
        running: true,
        commandPending: false,
      );
      addTearDown(subject.dispose);
      subject.startRecording();
      await subject.stopRecording();

      final confirmation = subject.confirmTransmission('Cấp cứu');
      await Future<void>.delayed(const Duration(milliseconds: 5));
      expect(subject.state.phase, TxPhase.transmitting);

      subject.setStationOnline(false);
      expect(subject.state.phase, TxPhase.failed);
      expect(subject.state.failure, TxFailure.stationOfflineDuringTx);
      expect(subject.canRetryTransmission, isFalse);

      repository.status = 'failed';
      await confirmation;
      expect(subject.state.phase, TxPhase.failed);
      expect(subject.state.draft?.status, 'failed');
      expect(subject.canRetryTransmission, isFalse);

      subject.setStationAvailability(
        online: true,
        running: true,
        commandPending: false,
      );
      expect(subject.canRetryTransmission, isTrue);
    },
  );

  test(
    'retry reconciles review draft and confirms again idempotently',
    () async {
      final repository = _LostConfirmRepository();
      final subject = TxController(
        stationId: 'station-1',
        repository: repository,
        queuePreviewDuration: Duration.zero,
      );
      subject.setStationAvailability(
        online: true,
        running: true,
        commandPending: false,
      );
      addTearDown(subject.dispose);
      subject.startRecording();
      await subject.stopRecording();

      await subject.confirmTransmission('Nội dung đã sửa');
      expect(subject.state.phase, TxPhase.failed);

      await subject.retry();

      expect(subject.state.phase, TxPhase.completed);
      expect(repository.confirmCalls, 2);
      expect(repository.retryCalls, 0);
    },
  );
}
