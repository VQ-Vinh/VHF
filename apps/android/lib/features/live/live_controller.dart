import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/legacy.dart';

import '../../models/station.dart';
import '../../providers.dart';

typedef DesiredStateSender =
    Future<void> Function({bool? running, String? targetLanguage, bool retry});

enum LiveCommandPhase {
  idle,
  sending,
  awaitingStation,
  applied,
  failed,
  offline,
}

@immutable
class LiveUxState {
  const LiveUxState({
    this.phase = LiveCommandPhase.idle,
    this.optimisticLanguage,
    this.previousLanguage,
    this.error,
    this.baselineGeneration,
    this.pendingRunning,
  });

  final LiveCommandPhase phase;
  final String? optimisticLanguage;
  final String? previousLanguage;
  final String? error;
  final int? baselineGeneration;
  final bool? pendingRunning;

  bool get busy =>
      phase == LiveCommandPhase.sending ||
      phase == LiveCommandPhase.awaitingStation;

  LiveUxState copyWith({
    LiveCommandPhase? phase,
    String? optimisticLanguage,
    String? previousLanguage,
    String? error,
    int? baselineGeneration,
    bool clearOptimisticLanguage = false,
    bool clearError = false,
    bool? pendingRunning,
    bool clearPendingRunning = false,
  }) => LiveUxState(
    phase: phase ?? this.phase,
    optimisticLanguage:
        clearOptimisticLanguage
            ? null
            : optimisticLanguage ?? this.optimisticLanguage,
    previousLanguage: previousLanguage ?? this.previousLanguage,
    error: clearError ? null : error ?? this.error,
    baselineGeneration: baselineGeneration ?? this.baselineGeneration,
    pendingRunning:
        clearPendingRunning ? null : pendingRunning ?? this.pendingRunning,
  );
}

class LiveUxController extends ChangeNotifier {
  LiveUxController({required this.stationId, required DesiredStateSender send})
    : _sendDesiredState = send;

  final String stationId;
  final DesiredStateSender _sendDesiredState;
  LiveUxState state = const LiveUxState();

  void synchronize(StationModel station, {required bool online}) {
    var next = state;
    if (!online && state.phase != LiveCommandPhase.offline) {
      next = next.copyWith(phase: LiveCommandPhase.offline);
    } else if (state.phase == LiveCommandPhase.awaitingStation &&
        station.observedGeneration >= station.desired.generation &&
        station.desired.generation > (state.baselineGeneration ?? -1)) {
      next = next.copyWith(
        phase: LiveCommandPhase.applied,
        clearOptimisticLanguage: true,
        clearError: true,
        clearPendingRunning: true,
      );
    } else if (online &&
        (state.phase == LiveCommandPhase.offline ||
            state.phase == LiveCommandPhase.applied)) {
      next = next.copyWith(
        phase: LiveCommandPhase.idle,
        clearError: true,
        clearPendingRunning: true,
      );
    }
    if (next != state) {
      state = next;
      notifyListeners();
    }
  }

  Future<void> setRunning(StationModel station, bool running) async {
    await _send(
      station,
      () => _sendDesiredState(running: running, retry: false),
      pendingRunning: running,
    );
  }

  Future<void> setLanguage(StationModel station, String language) async {
    state = state.copyWith(
      phase: LiveCommandPhase.sending,
      optimisticLanguage: language,
      previousLanguage: station.desired.targetLanguage,
      baselineGeneration: station.desired.generation,
      clearError: true,
    );
    notifyListeners();
    try {
      await _sendDesiredState(targetLanguage: language, retry: false);
      state = state.copyWith(phase: LiveCommandPhase.awaitingStation);
    } catch (error) {
      state = LiveUxState(
        phase: LiveCommandPhase.failed,
        optimisticLanguage: state.previousLanguage,
        previousLanguage: state.previousLanguage,
        error: error.toString(),
        baselineGeneration: state.baselineGeneration,
      );
    }
    notifyListeners();
  }

  Future<void> retry(StationModel station) async {
    await _send(station, () => _sendDesiredState(retry: true));
  }

  void dismissError() {
    state = state.copyWith(
      phase: LiveCommandPhase.idle,
      clearError: true,
      clearOptimisticLanguage: true,
      clearPendingRunning: true,
    );
    notifyListeners();
  }

  Future<void> _send(
    StationModel station,
    Future<void> Function() request, {
    bool? pendingRunning,
  }) async {
    state = state.copyWith(
      phase: LiveCommandPhase.sending,
      baselineGeneration: station.desired.generation,
      clearError: true,
      pendingRunning: pendingRunning,
    );
    notifyListeners();
    try {
      await request();
      state = state.copyWith(phase: LiveCommandPhase.awaitingStation);
    } catch (error) {
      state = state.copyWith(
        phase: LiveCommandPhase.failed,
        error: error.toString(),
        clearPendingRunning: true,
      );
    }
    notifyListeners();
  }
}

final liveUxControllerProvider = ChangeNotifierProvider.autoDispose
    .family<LiveUxController, String>((ref, stationId) {
      final api = ref.watch(apiProvider);
      return LiveUxController(
        stationId: stationId,
        send:
            ({running, targetLanguage, retry = false}) => api.setDesiredState(
              stationId,
              running: running,
              targetLanguage: targetLanguage,
              retry: retry,
            ),
      );
    });
