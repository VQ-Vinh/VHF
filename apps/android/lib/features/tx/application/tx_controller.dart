import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:uuid/uuid.dart';

import '../domain/tx_draft.dart';
import '../domain/tx_failure.dart';
import '../domain/tx_phase.dart';
import 'tx_repository.dart';
import 'tx_state.dart';
import 'tx_recorder.dart';

class TxController extends ChangeNotifier {
  TxController({
    required this.stationId,
    required TxRepository repository,
    TxRecorder? recorder,
    Duration maximumDuration = const Duration(seconds: 60),
    this.queuePreviewDuration = const Duration(seconds: 1),
  }) : _repository = repository,
       _recorder = recorder,
       _maximumDuration = maximumDuration,
       _recordingMaximumDuration = maximumDuration;

  final String stationId;
  final TxRepository _repository;
  final TxRecorder? _recorder;
  Duration _maximumDuration;
  Duration _recordingMaximumDuration;
  Duration get maximumDuration => _maximumDuration;
  Duration get recordingMaximumDuration => _recordingMaximumDuration;
  final Duration queuePreviewDuration;

  TxState state = const TxState();
  Timer? _recordingTimer;
  DateTime? _recordingStartedAt;
  bool _stationOnline = true;
  bool _stationRunning = false;
  bool _commandPending = false;
  bool _pttReady = true;
  bool _disposed = false;
  Future<void>? _recordingStart;
  String? _monitoredDraftId;
  String? _recordingRequestId;
  bool _restoreInProgress = false;
  String? _restoredDraftId;

  void setStationOnline(bool online) {
    if (_stationOnline == online) return;
    _stationOnline = online;
    if (!online &&
        (state.phase == TxPhase.queued ||
            state.phase == TxPhase.transmitting)) {
      state = state.copyWith(
        phase: TxPhase.failed,
        failure: TxFailure.stationOfflineDuringTx,
      );
      notifyListeners();
    } else if (!online && state.phase == TxPhase.idle) {
      state = state.copyWith(
        phase: TxPhase.stationOffline,
        failure: TxFailure.stationOffline,
      );
      notifyListeners();
    } else if (online && state.phase == TxPhase.stationOffline) {
      reset();
    }
  }

  void setStationAvailability({
    required bool online,
    required bool running,
    required bool commandPending,
    bool pttReady = true,
  }) {
    setStationOnline(online);
    final pttChanged = _pttReady != pttReady;
    if (_stationRunning == running &&
        _commandPending == commandPending &&
        !pttChanged) {
      return;
    }
    _stationRunning = running;
    _commandPending = commandPending;
    _pttReady = pttReady;
    if (!pttReady &&
        (state.phase == TxPhase.idle ||
            state.phase == TxPhase.queued ||
            state.phase == TxPhase.transmitting)) {
      state = state.copyWith(
        phase: TxPhase.failed,
        failure: TxFailure.pttUnavailable,
      );
    } else if (pttReady &&
        state.failure == TxFailure.pttUnavailable &&
        state.draft == null) {
      state = const TxState();
    }
    notifyListeners();
  }

  bool get canStartRecording =>
      state.canStartRecording &&
      _stationOnline &&
      _stationRunning &&
      _pttReady &&
      !_commandPending;

  bool get startRequired => _stationOnline && !_stationRunning;

  bool get canRetryTransmission =>
      state.phase == TxPhase.failed &&
      state.draft != null &&
      (state.failure != TxFailure.stationOfflineDuringTx ||
          state.draft?.status == 'failed') &&
      _stationOnline &&
      _stationRunning &&
      _pttReady &&
      !_commandPending;

  void setTargetLanguage(String language) {
    if (!state.canChangeLanguage || language == state.targetLanguage) return;
    state = state.copyWith(targetLanguage: language);
    notifyListeners();
  }

  void setMaximumDuration(Duration value) {
    final seconds = value.inSeconds.clamp(5, 120);
    final normalized = Duration(seconds: seconds);
    if (_maximumDuration == normalized) return;
    _maximumDuration = normalized;
    if (state.phase != TxPhase.recording) {
      _recordingMaximumDuration = normalized;
    }
    notifyListeners();
  }

  void startRecording() {
    if (!_stationOnline) {
      _fail(TxFailure.stationOffline, TxPhase.stationOffline);
      return;
    }
    if (!canStartRecording) return;
    _recordingStartedAt = DateTime.now();
    _recordingRequestId = const Uuid().v4();
    _recordingMaximumDuration = _maximumDuration;
    state = state.copyWith(
      phase: TxPhase.recording,
      duration: Duration.zero,
      clearDraft: true,
      clearFailure: true,
    );
    notifyListeners();
    final recorder = _recorder;
    if (recorder != null) {
      _recordingStart = recorder.start().catchError((Object _) {
        if (!_disposed) _fail(TxFailure.processingFailed, TxPhase.failed);
      });
    }
    _recordingTimer = Timer.periodic(const Duration(milliseconds: 100), (_) {
      final started = _recordingStartedAt;
      if (started == null) return;
      final elapsed = DateTime.now().difference(started);
      final limit = _recordingMaximumDuration;
      state = state.copyWith(duration: elapsed > limit ? limit : elapsed);
      notifyListeners();
      if (elapsed >= limit) {
        unawaited(stopRecording());
      }
    });
  }

  Future<void> stopRecording() async {
    if (state.phase != TxPhase.recording) return;
    _stopRecordingTimer();
    final duration =
        state.duration == Duration.zero
            ? const Duration(milliseconds: 100)
            : state.duration;
    String? audioPath;
    try {
      await _recordingStart;
      audioPath = await _recorder?.stop();
      _recordingStart = null;
    } catch (_) {
      if (!_disposed) _fail(TxFailure.processingFailed, TxPhase.failed);
      return;
    }
    state = state.copyWith(phase: TxPhase.processing, duration: duration);
    notifyListeners();
    try {
      final draft = await _repository.processRecording(
        TxRecordingInput(
          stationId: stationId,
          duration: duration,
          targetLanguage: state.targetLanguage,
          requestId: _recordingRequestId ?? const Uuid().v4(),
          audioPath: audioPath,
        ),
      );
      if (_disposed || state.phase != TxPhase.processing) return;
      state = state.copyWith(phase: TxPhase.reviewReady, draft: draft);
      notifyListeners();
    } on TxRecordingTooLong catch (error) {
      if (!_disposed) {
        setMaximumDuration(Duration(seconds: error.maximumSeconds));
        _fail(TxFailure.recordingTooLong, TxPhase.failed);
      }
    } catch (_) {
      if (!_disposed) {
        _fail(TxFailure.processingFailed, TxPhase.failed);
      }
    }
  }

  Future<void> confirmTransmission(String translation) async {
    final draft = state.draft;
    if (state.phase != TxPhase.reviewReady || draft == null) return;
    final normalized = translation.trim();
    if (normalized.isEmpty || normalized.length > 2000) return;
    final confirmedDraft = draft.copyWith(
      translation: normalized,
      status: 'synthesizing',
    );
    state = state.copyWith(
      phase: TxPhase.processing,
      draft: confirmedDraft,
      clearFailure: true,
    );
    notifyListeners();
    try {
      await _repository.confirmTransmission(draft, normalized);
      if (_disposed || state.phase != TxPhase.processing) return;
      state = state.copyWith(phase: TxPhase.queued, draft: confirmedDraft);
      notifyListeners();
      await _monitorTransmission(confirmedDraft);
    } catch (error, stackTrace) {
      if (kDebugMode) {
        debugPrint('TX confirm failed: $error');
        debugPrintStack(stackTrace: stackTrace);
      }
      if (!_disposed) {
        _fail(_failureFor(error), TxPhase.failed);
      }
    }
  }

  Future<void> cancelDraft() async {
    final draft = state.draft;
    if (draft != null && draft.status != 'review_ready') return;
    _stopRecordingTimer();
    await _recorder?.cancel();
    final draftId = state.draft?.id;
    state = TxState(targetLanguage: state.targetLanguage);
    notifyListeners();
    if (draftId != null) {
      await _repository.cancelDraft(draftId);
    }
  }

  Future<void> cancelRecordingForBackground() async {
    if (state.phase != TxPhase.recording) return;
    _stopRecordingTimer();
    _recordingStart = null;
    _recordingRequestId = null;
    await _recorder?.cancel();
    state = TxState(targetLanguage: state.targetLanguage);
    notifyListeners();
  }

  Future<void> retry() async {
    if (state.failure == TxFailure.pttUnavailable && !_pttReady) return;
    final localDraft = state.draft;
    if (state.phase == TxPhase.failed && localDraft != null) {
      if (!canRetryTransmission) return;
      state = state.copyWith(phase: TxPhase.processing, clearFailure: true);
      notifyListeners();
      try {
        final current = await _repository.getDraft(stationId, localDraft.id);
        if (_disposed) return;
        if (current.status == 'completed') {
          state = state.copyWith(phase: TxPhase.completed, draft: current);
          notifyListeners();
          return;
        }
        if (current.status == 'queued' ||
            current.status == 'synthesizing' ||
            current.status == 'claimed' ||
            current.status == 'transmitting') {
          state = state.copyWith(
            phase:
                current.status == 'claimed' || current.status == 'transmitting'
                    ? TxPhase.transmitting
                    : TxPhase.queued,
            draft: current,
          );
          notifyListeners();
          await _monitorTransmission(current);
          return;
        }
        TxDraft retryDraft;
        if (current.status == 'review_ready') {
          await _repository.confirmTransmission(
            localDraft,
            localDraft.translation,
          );
          retryDraft = localDraft.copyWith(status: 'queued');
        } else if (current.status == 'failed') {
          retryDraft = await _repository.retryTransmission(current);
        } else {
          _fail(TxFailure.transmissionFailed, TxPhase.failed);
          return;
        }
        state = state.copyWith(
          phase: TxPhase.queued,
          draft: retryDraft,
          clearFailure: true,
        );
        notifyListeners();
        await _monitorTransmission(retryDraft);
      } catch (error, stackTrace) {
        if (kDebugMode) {
          debugPrint('TX retry failed: $error');
          debugPrintStack(stackTrace: stackTrace);
        }
        _fail(_failureFor(error), TxPhase.failed);
      }
      return;
    }
    reset();
  }

  Future<void> restoreActiveTransmission({String? stationJobId}) async {
    if (_restoreInProgress || _monitoredDraftId != null) return;
    _restoreInProgress = true;
    try {
      final stored = await _repository.activeDraftId(stationId);
      final draftId =
          stationJobId != null && stationJobId.isNotEmpty
              ? stationJobId
              : stored;
      if (draftId == null || draftId.isEmpty) return;
      if (_restoredDraftId == draftId) return;
      _restoredDraftId = draftId;
      final current = await _repository.getDraft(stationId, draftId);
      if (_disposed) return;
      if (current.status == 'completed' || current.status == 'cancelled') {
        await _repository.clearActiveDraft(stationId);
        if (current.status == 'completed') {
          state = state.copyWith(phase: TxPhase.completed, draft: current);
          notifyListeners();
        }
        return;
      }
      state = state.copyWith(
        phase:
            current.status == 'review_ready'
                ? TxPhase.reviewReady
                : current.status == 'claimed' ||
                    current.status == 'transmitting'
                ? TxPhase.transmitting
                : current.status == 'failed'
                ? TxPhase.failed
                : TxPhase.queued,
        draft: current,
        failure:
            current.status == 'failed' ? TxFailure.transmissionFailed : null,
        clearFailure: current.status != 'failed',
      );
      notifyListeners();
      if (current.status != 'failed') await _monitorTransmission(current);
    } on TxPermanentPollingFailure {
      if (!_disposed) _fail(TxFailure.transmissionFailed, TxPhase.failed);
    } catch (_) {
      // A transient startup failure is retried on the next Station update.
      _restoredDraftId = null;
    } finally {
      _restoreInProgress = false;
    }
  }

  void reset() {
    _stopRecordingTimer();
    state = TxState(targetLanguage: state.targetLanguage);
    notifyListeners();
  }

  Future<void> _monitorTransmission(TxDraft draft) async {
    _monitoredDraftId = draft.id;
    var retryDelay = queuePreviewDuration;
    while (!_disposed && _monitoredDraftId == draft.id) {
      await Future<void>.delayed(retryDelay);
      TxDraft current;
      try {
        current = await _repository.getDraft(stationId, draft.id);
        retryDelay = queuePreviewDuration;
      } on TxPermanentPollingFailure {
        _monitoredDraftId = null;
        _fail(TxFailure.transmissionFailed, TxPhase.failed);
        return;
      } catch (_) {
        final nextMilliseconds = (retryDelay.inMilliseconds * 2).clamp(
          queuePreviewDuration.inMilliseconds,
          5000,
        );
        retryDelay = Duration(milliseconds: nextMilliseconds);
        continue;
      }
      if (_disposed) return;
      if (current.status == 'claimed' || current.status == 'transmitting') {
        if (_stationOnline) {
          state = state.copyWith(
            phase: TxPhase.transmitting,
            draft: current,
            clearFailure: true,
          );
        } else {
          state = state.copyWith(draft: current);
        }
      } else if (current.status == 'completed') {
        state = state.copyWith(phase: TxPhase.completed, draft: current);
        _monitoredDraftId = null;
        unawaited(_repository.clearActiveDraft(stationId));
      } else if (current.status == 'failed') {
        final failure =
            current.error == 'STATION_OFFLINE_DURING_TX'
                ? TxFailure.stationOfflineDuringTx
                : _failureForCode(current.error);
        state = state.copyWith(
          phase: TxPhase.failed,
          draft: current,
          failure: failure,
        );
        _monitoredDraftId = null;
      } else {
        state = state.copyWith(draft: current);
      }
      notifyListeners();
    }
  }

  void _fail(TxFailure failure, TxPhase phase) {
    _stopRecordingTimer();
    state = state.copyWith(phase: phase, failure: failure);
    notifyListeners();
  }

  TxFailure _failureFor(Object error) =>
      error is TxOperationFailure
          ? _failureForCode(error.code)
          : TxFailure.transmissionFailed;

  TxFailure _failureForCode(String? code) => switch (code) {
    'PTT_UNAVAILABLE' => TxFailure.pttUnavailable,
    'TX_OUTPUT_TOO_LONG' => TxFailure.outputTooLong,
    'TX_SYNTHESIS_TIMEOUT' => TxFailure.synthesisTimeout,
    'TX_PLAYBACK_TIMEOUT' => TxFailure.playbackTimeout,
    _ => TxFailure.transmissionFailed,
  };

  void _stopRecordingTimer() {
    _recordingTimer?.cancel();
    _recordingTimer = null;
    _recordingStartedAt = null;
  }

  @override
  void dispose() {
    _disposed = true;
    _monitoredDraftId = null;
    _stopRecordingTimer();
    unawaited(_recorder?.dispose() ?? Future<void>.value());
    super.dispose();
  }
}
