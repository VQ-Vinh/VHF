import 'dart:async';

import 'package:flutter/foundation.dart';

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
    this.maximumDuration = const Duration(seconds: 60),
    this.queuePreviewDuration = const Duration(seconds: 1),
  }) : _repository = repository,
       _recorder = recorder;

  final String stationId;
  final TxRepository _repository;
  final TxRecorder? _recorder;
  final Duration maximumDuration;
  final Duration queuePreviewDuration;

  TxState state = const TxState();
  Timer? _recordingTimer;
  DateTime? _recordingStartedAt;
  bool _stationOnline = true;
  bool _disposed = false;
  Future<void>? _recordingStart;

  void setStationOnline(bool online) {
    if (_stationOnline == online) return;
    _stationOnline = online;
    if (!online && state.phase == TxPhase.idle) {
      state = state.copyWith(
        phase: TxPhase.stationOffline,
        failure: TxFailure.stationOffline,
      );
      notifyListeners();
    } else if (online && state.phase == TxPhase.stationOffline) {
      reset();
    }
  }

  void setTargetLanguage(String language) {
    if (!state.canChangeLanguage || language == state.targetLanguage) return;
    state = state.copyWith(targetLanguage: language);
    notifyListeners();
  }

  void startRecording() {
    if (!_stationOnline) {
      _fail(TxFailure.stationOffline, TxPhase.stationOffline);
      return;
    }
    if (!state.canStartRecording) return;
    _recordingStartedAt = DateTime.now();
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
      state = state.copyWith(
        duration: elapsed > maximumDuration ? maximumDuration : elapsed,
      );
      notifyListeners();
      if (elapsed >= maximumDuration) {
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
          audioPath: audioPath,
        ),
      );
      if (_disposed || state.phase != TxPhase.processing) return;
      state = state.copyWith(phase: TxPhase.reviewReady, draft: draft);
      notifyListeners();
    } catch (_) {
      if (!_disposed) {
        _fail(TxFailure.processingFailed, TxPhase.failed);
      }
    }
  }

  Future<void> confirmTransmission() async {
    final draft = state.draft;
    if (state.phase != TxPhase.reviewReady || draft == null) return;
    state = state.copyWith(phase: TxPhase.queued, clearFailure: true);
    notifyListeners();
    try {
      await _repository.confirmTransmission(draft);
      await _monitorTransmission(draft);
    } catch (_) {
      if (!_disposed) {
        _fail(TxFailure.transmissionFailed, TxPhase.failed);
      }
    }
  }

  Future<void> cancelDraft() async {
    _stopRecordingTimer();
    await _recorder?.cancel();
    final draftId = state.draft?.id;
    state = TxState(targetLanguage: state.targetLanguage);
    notifyListeners();
    if (draftId != null) {
      await _repository.cancelDraft(draftId);
    }
  }

  Future<void> retry() async {
    if (state.phase == TxPhase.failed && state.draft != null) {
      try {
        final retryDraft = await _repository.retryTransmission(state.draft!);
        state = state.copyWith(
          phase: TxPhase.queued,
          draft: retryDraft,
          clearFailure: true,
        );
        notifyListeners();
        await _monitorTransmission(retryDraft);
      } catch (_) {
        _fail(TxFailure.transmissionFailed, TxPhase.failed);
      }
      return;
    }
    reset();
  }

  void reset() {
    _stopRecordingTimer();
    state = TxState(targetLanguage: state.targetLanguage);
    notifyListeners();
  }

  Future<void> _monitorTransmission(TxDraft draft) async {
    while (!_disposed &&
        (state.phase == TxPhase.queued ||
            state.phase == TxPhase.transmitting)) {
      await Future<void>.delayed(queuePreviewDuration);
      final current = await _repository.getDraft(stationId, draft.id);
      if (_disposed) return;
      if (current.status == 'claimed' || current.status == 'transmitting') {
        state = state.copyWith(phase: TxPhase.transmitting, draft: current);
      } else if (current.status == 'completed') {
        state = state.copyWith(phase: TxPhase.completed, draft: current);
      } else if (current.status == 'failed') {
        _fail(TxFailure.transmissionFailed, TxPhase.failed);
        return;
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

  void _stopRecordingTimer() {
    _recordingTimer?.cancel();
    _recordingTimer = null;
    _recordingStartedAt = null;
  }

  @override
  void dispose() {
    _disposed = true;
    _stopRecordingTimer();
    unawaited(_recorder?.dispose() ?? Future<void>.value());
    super.dispose();
  }
}
