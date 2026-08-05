import '../../../services/prana_api.dart';
import '../domain/tx_draft.dart';
import 'tx_repository.dart';

class ApiTxRepository implements TxRepository {
  ApiTxRepository(this.api);
  final PranaApi api;
  final Map<String, String> _stationByDraft = {};

  @override
  Future<TxDraft> processRecording(TxRecordingInput input) {
    final path = input.audioPath;
    if (path == null || path.isEmpty) throw StateError('TX_AUDIO_MISSING');
    return api.createTxDraft(input.stationId, path, input.targetLanguage).then((
      draft,
    ) {
      _stationByDraft[draft.id] = input.stationId;
      return draft;
    });
  }

  @override
  Future<void> confirmTransmission(TxDraft draft) =>
      api.confirmTxDraft(draft.stationId, draft.id);

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
