import 'dart:async';

import 'package:flutter/foundation.dart';

import '../domain/tx_draft.dart';
import '../domain/tx_failure.dart';
import '../domain/tx_phase.dart';
import 'tx_repository.dart';
import 'tx_state.dart';

class TxController extends ChangeNotifier {
  TxController({
    required this.stationId,
    required TxRepository repository,
    this.maximumDuration = const Duration(seconds: 60),
    this.queuePreviewDuration = const Duration(milliseconds: 450),
  }) : _repository = repository;

  final String stationId;
  final TxRepository _repository;
  final Duration maximumDuration;
  final Duration queuePreviewDuration;

  TxState state = const TxState();
  Timer? _recordingTimer;
  DateTime? _recordingStartedAt;
  bool _stationOnline = true;
  bool _disposed = false;

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
    state = state.copyWith(phase: TxPhase.processing, duration: duration);
    notifyListeners();
    try {
      final draft = await _repository.processRecording(
        TxRecordingInput(
          stationId: stationId,
          duration: duration,
          targetLanguage: state.targetLanguage,
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
    await Future<void>.delayed(queuePreviewDuration);
    if (_disposed || state.phase != TxPhase.queued) return;
    state = state.copyWith(phase: TxPhase.transmitting);
    notifyListeners();
    try {
      await _repository.confirmTransmission(draft);
      if (_disposed || state.phase != TxPhase.transmitting) return;
      state = state.copyWith(phase: TxPhase.completed);
      notifyListeners();
    } catch (_) {
      if (!_disposed) {
        _fail(TxFailure.transmissionFailed, TxPhase.failed);
      }
    }
  }

  Future<void> cancelDraft() async {
    _stopRecordingTimer();
    final draftId = state.draft?.id;
    state = TxState(targetLanguage: state.targetLanguage);
    notifyListeners();
    if (draftId != null) {
      await _repository.cancelDraft(draftId);
    }
  }

  Future<void> retry() async {
    if (state.phase == TxPhase.failed && state.draft != null) {
      state = state.copyWith(phase: TxPhase.reviewReady, clearFailure: true);
      notifyListeners();
      return;
    }
    reset();
  }

  void reset() {
    _stopRecordingTimer();
    state = TxState(targetLanguage: state.targetLanguage);
    notifyListeners();
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
    super.dispose();
  }
}
