import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:prana_mobile/telemetry/domain/telemetry_repository.dart';

enum TelemetryFreshness { missing, fresh, stale, error }

class StationTelemetryState {
  const StationTelemetryState({
    this.snapshot,
    this.freshness = TelemetryFreshness.missing,
  });
  final TelemetrySnapshot? snapshot;
  final TelemetryFreshness freshness;
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
    state = StationTelemetryState(snapshot: state.snapshot);
    notifyListeners();
    _subscription = repository
        .watch(stationId)
        .listen(
          (sample) {
            if (_disposed || epoch != _epoch) return;
            state = StationTelemetryState(
              snapshot: sample,
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
