import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/features/tx/application/fake_tx_repository.dart';
import 'package:prana_mobile/features/tx/application/tx_controller.dart';
import 'package:prana_mobile/features/tx/domain/tx_phase.dart';

void main() {
  TxController controller({
    Object? processingError,
    Object? transmissionError,
  }) => TxController(
    stationId: 'station-1',
    repository: FakeTxRepository(
      processingDelay: Duration.zero,
      transmissionDelay: Duration.zero,
      processingError: processingError,
      transmissionError: transmissionError,
    ),
    queuePreviewDuration: Duration.zero,
  );

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

  test('confirm cannot be submitted twice', () async {
    final subject = controller();
    addTearDown(subject.dispose);
    subject.startRecording();
    await subject.stopRecording();

    final first = subject.confirmTransmission();
    final second = subject.confirmTransmission();
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

  test('offline station blocks recording', () {
    final subject = controller();
    addTearDown(subject.dispose);

    subject.setStationOnline(false);
    subject.startRecording();

    expect(subject.state.phase, TxPhase.stationOffline);
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

      await subject.confirmTransmission();
      expect(subject.state.phase, TxPhase.failed);

      await subject.retry();
      expect(subject.state.phase, TxPhase.completed);
    },
  );
}
