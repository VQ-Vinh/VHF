import '../domain/tx_draft.dart';

abstract interface class TxRepository {
  Future<TxDraft> processRecording(TxRecordingInput input);

  Future<void> confirmTransmission(TxDraft draft);

  Future<void> cancelDraft(String draftId);

  Future<TxDraft> getDraft(String stationId, String draftId);

  Future<TxDraft> retryTransmission(TxDraft draft);
}
