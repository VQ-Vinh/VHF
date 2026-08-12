import '../../../services/prana_api.dart';
import '../domain/tx_draft.dart';
import 'tx_repository.dart';

class ApiTxRepository implements TxRepository {
  ApiTxRepository(this.api);
  final PranaApi api;
  final Map<String, String> _stationByDraft = {};

  @override
  Future<TxDraft> processRecording(TxRecordingInput input) async {
    final path = input.audioPath;
    if (path == null || path.isEmpty) throw StateError('TX_AUDIO_MISSING');
    try {
      final draft = await api.createTxDraft(
        input.stationId,
        path,
        input.targetLanguage,
      );
      _stationByDraft[draft.id] = input.stationId;
      return draft;
    } on PranaApiFailure catch (error) {
      if (error.code == 'TX_AUDIO_TOO_LONG') {
        throw TxRecordingTooLong(error.maxSeconds ?? 60);
      }
      rethrow;
    }
  }

  @override
  Future<void> confirmTransmission(TxDraft draft, String translation) =>
      api.confirmTxDraft(draft.stationId, draft.id, translation);

  @override
  Future<void> cancelDraft(String draftId) {
    final stationId = _stationByDraft[draftId];
    if (stationId == null) return Future<void>.value();
    return api.cancelTxDraft(stationId, draftId);
  }

  @override
  Future<TxDraft> getDraft(String stationId, String draftId) =>
      api.txDraft(stationId, draftId);

  @override
  Future<TxDraft> retryTransmission(TxDraft draft) =>
      api.retryTxDraft(draft.stationId, draft.id);
}
