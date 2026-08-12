import '../domain/tx_draft.dart';

class TxRecordingTooLong implements Exception {
  const TxRecordingTooLong(this.maximumSeconds);

  final int maximumSeconds;
}

abstract interface class TxRepository {
  Future<TxDraft> processRecording(TxRecordingInput input);

  Future<void> confirmTransmission(TxDraft draft, String translation);

  Future<void> cancelDraft(String draftId);

  Future<TxDraft> getDraft(String stationId, String draftId);

  Future<TxDraft> retryTransmission(TxDraft draft);
}
