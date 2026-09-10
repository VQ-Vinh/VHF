import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:prana_mobile/telemetry/domain/telemetry_repository.dart';

enum TelemetryFreshness { missing, fresh, stale, error }

/// How many samples the instruments may draw a trend from.
///
/// One sample a second, so this is the last half minute or so. Enough for a
/// readable sparkline without holding history nobody reads.
const int telemetryHistoryLength = 40;

class StationTelemetryState {
  const StationTelemetryState({
    this.snapshot,
    this.previous,
    this.history = const [],
    this.freshness = TelemetryFreshness.missing,
  });
  final TelemetrySnapshot? snapshot;

  /// The sample before [snapshot], or null until two have arrived. The
  /// repository publishes absolute readings only, so a change per tick has to
  /// be derived here rather than read off the wire.
  final TelemetrySnapshot? previous;

  /// Oldest first, newest last, capped at [telemetryHistoryLength].
  final List<TelemetrySnapshot> history;
  final TelemetryFreshness freshness;

  double? get speedDelta =>
      previous == null || snapshot == null
          ? null
          : snapshot!.speedKnots - previous!.speedKnots;

  double? get depthDelta =>
      previous == null || snapshot == null
          ? null
          : snapshot!.depthMetres - previous!.depthMetres;
}

class StationTelemetryController extends ChangeNotifier {
  StationTelemetryController(
    this.repository,
    this.stationId, {
    DateTime Function()? clock,
  }) : _clock = clock ?? DateTime.now {
    retry();
    _freshnessTimer = Timer.periodic(
      const Duration(seconds: 1),
      (_) => refreshFreshness(),
    );
  }
  final TelemetryRepository repository;
  final String stationId;
  final DateTime Function() _clock;
  StationTelemetryState state = const StationTelemetryState();
  StreamSubscription<TelemetrySnapshot>? _subscription;
  Timer? _freshnessTimer;
  bool _disposed = false;
  int _epoch = 0;

  Future<void> retry() async {
    final epoch = ++_epoch;
    await _subscription?.cancel();
    if (_disposed || epoch != _epoch) return;
    // Keep the reading and its trend on screen while reconnecting; blanking
    // them would read as "the boat lost way", which is not what happened.
    state = StationTelemetryState(
      snapshot: state.snapshot,
      previous: state.previous,
      history: state.history,
    );
    notifyListeners();
    _subscription = repository
        .watch(stationId)
        .listen(
          (sample) {
            if (_disposed || epoch != _epoch) return;
            final history = [...state.history, sample];
            state = StationTelemetryState(
              snapshot: sample,
              previous: state.snapshot,
              history:
                  history.length > telemetryHistoryLength
                      ? history.sublist(history.length - telemetryHistoryLength)
                      : history,
              freshness:
                  _clock().difference(sample.timestamp) >
                          const Duration(seconds: 5)
                      ? TelemetryFreshness.stale
                      : TelemetryFreshness.fresh,
            );
            notifyListeners();
          },
          onError: (Object error) {
            if (_disposed || epoch != _epoch) return;
            state = StationTelemetryState(
              snapshot: state.snapshot,
              previous: state.previous,
              history: state.history,
              freshness: TelemetryFreshness.error,
            );
            notifyListeners();
          },
        );
  }

  void refreshFreshness() {
    final sample = state.snapshot;
    if (_disposed ||
        sample == null ||
        state.freshness != TelemetryFreshness.fresh) {
      return;
    }
    if (_clock().difference(sample.timestamp) > const Duration(seconds: 5)) {
      state = StationTelemetryState(
        snapshot: sample,
        previous: state.previous,
        history: state.history,
        freshness: TelemetryFreshness.stale,
      );
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _disposed = true;
    _epoch++;
    _freshnessTimer?.cancel();
    _subscription?.cancel();
    super.dispose();
  }
}
