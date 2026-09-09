import 'dart:io';
import 'package:prana_mobile/core/cancellable_delay.dart';
import 'package:prana_mobile/data/network/prana_api.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:prana_mobile/domain/radio/tx/tx_draft.dart';
import 'package:prana_mobile/domain/radio/tx/tx_repository.dart';

class ApiTxRepository implements TxRepository, TxRepositoryLifecycle {
  ApiTxRepository(
    this.api, {
    this.identityScope = '',
    FlutterSecureStorage storage = const FlutterSecureStorage(),
  }) : _storage = storage;
  final PranaApi api;
  final String identityScope;
  final FlutterSecureStorage _storage;
  final Map<String, String> _stationByDraft = {};
  bool _closed = false;
  final _pollDelay = CancellableDelay();
  void _checkOpen() {
    if (_closed) throw StateError('TX_SESSION_CLOSED');
  }

  @override
  void close() {
    _closed = true;
    _pollDelay.close();
    _stationByDraft.clear();
  }

  @override
  Future<TxDraft> processRecording(TxRecordingInput input) async {
    final path = input.audioPath;
    if (path == null || path.isEmpty) throw StateError('TX_AUDIO_MISSING');
    try {
      _checkOpen();
      final draft = await api.createTxDraft(
        input.stationId,
        path,
        input.targetLanguage,
        input.requestId,
      );
      _checkOpen();
      var resolved = draft;
      var delay = const Duration(milliseconds: 500);
      while (resolved.status == 'processing') {
        await _pollDelay.wait(delay);
        _checkOpen();
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
      _checkOpen();
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
    } finally {
      try {
        final file = File(path);
        if (await file.exists()) await file.delete();
      } on FileSystemException {
        // Recorder disposal can already have removed this temporary file.
      }
    }
  }

  @override
  Future<void> confirmTransmission(TxDraft draft, String translation) async {
    _checkOpen();
    await _storage.write(key: _trackingKey(draft.stationId), value: draft.id);
    _checkOpen();
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
    _checkOpen();
    TxDraft draft;
    _stationByDraft[draftId] = stationId;
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
    _checkOpen();
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

  String _trackingKey(String stationId) =>
      'tx_active_${identityScope}_$stationId';
}
