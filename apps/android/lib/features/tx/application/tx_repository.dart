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

  Future<String?> activeDraftId(String stationId);

  Future<void> clearActiveDraft(String stationId);
}

class TxPermanentPollingFailure implements Exception {
  const TxPermanentPollingFailure(this.code);

  final String code;
}

class TxOperationFailure implements Exception {
  const TxOperationFailure(this.code);

  final String code;
}
