import 'package:flutter/foundation.dart';
import 'package:prana_mobile/telemetry/domain/telemetry_repository.dart';
import 'package:prana_mobile/domain/station/station.dart';
import 'package:prana_mobile/domain/account/plan_entitlements.dart';
import 'package:prana_mobile/runtime/vhf/live_controller.dart';
import 'package:prana_mobile/runtime/vhf/tx_controller.dart';

/// Phone-side session only. Remote capture/VAD/processing remain on Station/Cloud.
class StationRuntimeState {
  const StationRuntimeState({
    this.station,
    this.online = false,
    this.apiOnline = false,
    this.telemetry,
    this.viewOnly = false,
  });
  final StationModel? station;
  final bool online;
  final bool apiOnline;
  final TelemetrySnapshot? telemetry;

  /// A remote operator holds the control lease. Everything stays readable;
  /// only the controls are withdrawn.
  final bool viewOnly;

  StationRuntimeState withTelemetry(TelemetrySnapshot? sample) =>
      StationRuntimeState(
        station: station,
        online: online,
        apiOnline: apiOnline,
        telemetry: sample,
        viewOnly: viewOnly,
      );
}

class StationSession extends ChangeNotifier {
  StationSession({
    required this.uid,
    required this.stationId,
    required this.rx,
    required this.tx,
  }) {
    rx.addListener(_changed);
    tx.addListener(_changed);
  }
  final String uid;
  final String stationId;
  final LiveUxController rx;
  final TxController tx;
  StationRuntimeState state = const StationRuntimeState();
  bool _disposed = false;
  void _changed() {
    if (!_disposed) notifyListeners();
  }

  void synchronize(
    StationModel station,
    DateTime now,
    PlanEntitlements entitlements,
    bool apiOnline,
  ) {
    if (_disposed) return;
    final online = station.isOnlineAt(now);
    // The 1 Hz clock that already drives this call is what expires the lease:
    // when it lapses, the next tick simply reports viewOnly false again.
    final viewOnly = station.controlHeldByOther(now);
    state = StationRuntimeState(
      station: station,
      online: online,
      apiOnline: apiOnline,
      viewOnly: viewOnly,
    );
    rx.synchronize(station, online: online, viewOnly: viewOnly);
    tx.setStationAvailability(
      online: online,
      running: station.desired.running,
      commandPending: station.commandPending || rx.state.busy,
      pttReady: station.pttReady,
      viewOnly: viewOnly,
    );
    tx.setMaximumDuration(
      Duration(seconds: entitlements.txMaxRecordingSeconds),
    );
    tx.restoreActiveTransmission(stationJobId: station.txJobId);
    _changed();
  }

  @override
  void dispose() {
    _disposed = true;
    rx.removeListener(_changed);
    tx.removeListener(_changed);
    rx.dispose();
    tx.dispose();
    super.dispose();
  }
}
