import '../../../services/prana_api.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../domain/tx_draft.dart';
import 'tx_repository.dart';

class ApiTxRepository implements TxRepository {
  ApiTxRepository(
    this.api, {
    FlutterSecureStorage storage = const FlutterSecureStorage(),
  }) : _storage = storage;
  final PranaApi api;
  final FlutterSecureStorage _storage;
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
        input.requestId,
      );
      var resolved = draft;
      var delay = const Duration(milliseconds: 500);
      while (resolved.status == 'processing') {
        await Future<void>.delayed(delay);
        try {
          resolved = await api.txDraft(input.stationId, input.requestId);
        } on PranaApiFailure catch (error) {
          if (error.messageKey != 'error_connection_timeout' &&
              error.messageKey != 'error_request_timeout' &&
              error.messageKey != 'error_api_unreachable') {
            rethrow;
          }
          continue;
        }
        if (delay < const Duration(seconds: 5)) {
          delay *= 2;
        }
      }
      if (resolved.status == 'failed') {
        throw StateError(resolved.error ?? 'TX_PROCESSING_FAILED');
      }
      _stationByDraft[resolved.id] = input.stationId;
      return resolved;
    } on PranaApiFailure catch (error) {
      if (error.code == 'TX_AUDIO_TOO_LONG') {
        throw TxRecordingTooLong(error.maxSeconds ?? 60);
      }
      throw TxOperationFailure(error.code ?? 'TX_PROCESSING_FAILED');
    }
  }

  @override
  Future<void> confirmTransmission(TxDraft draft, String translation) async {
    await _storage.write(key: _trackingKey(draft.stationId), value: draft.id);
    try {
      await api.confirmTxDraft(draft.stationId, draft.id, translation);
    } on PranaApiFailure catch (error) {
      throw TxOperationFailure(error.code ?? 'TX_PROCESSING_FAILED');
    }
  }

  @override
  Future<void> cancelDraft(String draftId) {
    final stationId = _stationByDraft[draftId];
    if (stationId == null) return Future<void>.value();
    return api.cancelTxDraft(stationId, draftId);
  }

  @override
  Future<TxDraft> getDraft(String stationId, String draftId) async {
    TxDraft draft;
    try {
      draft = await api.txDraft(stationId, draftId);
    } on PranaApiFailure catch (error) {
      if (error.code == 'TX_NOT_FOUND' ||
          error.code == 'STATION_NOT_FOUND' ||
          error.code == 'FORBIDDEN') {
        throw TxPermanentPollingFailure(error.code ?? 'TX_NOT_FOUND');
      }
      rethrow;
    }
    if (draft.status == 'completed' || draft.status == 'cancelled') {
      await clearActiveDraft(stationId);
    }
    return draft;
  }

  @override
  Future<TxDraft> retryTransmission(TxDraft draft) async {
    TxDraft retried;
    try {
      retried = await api.retryTxDraft(draft.stationId, draft.id);
    } on PranaApiFailure catch (error) {
      throw TxOperationFailure(error.code ?? 'TX_PROCESSING_FAILED');
    }
    await _storage.write(key: _trackingKey(draft.stationId), value: retried.id);
    return retried;
  }

  @override
  Future<String?> activeDraftId(String stationId) =>
      _storage.read(key: _trackingKey(stationId));

  @override
  Future<void> clearActiveDraft(String stationId) =>
      _storage.delete(key: _trackingKey(stationId));

  static String _trackingKey(String stationId) => 'tx_active_$stationId';
}
