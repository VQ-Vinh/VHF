import 'package:prana_mobile/core/cancellable_delay.dart';
import 'package:flutter/foundation.dart';
import 'package:prana_mobile/domain/station/station.dart';
import 'package:prana_mobile/domain/station/station_repository.dart';

class StationSettingsController extends ChangeNotifier {
  StationSettingsController(this.repository, this.stationId, this.readStation);
  final StationRepository repository;
  final String stationId;
  final StationModel? Function() readStation;
  bool saving = false, applying = false, refreshing = false;
  String? error;
  String? refreshResultKey;
  bool _disposed = false;
  final _delay = CancellableDelay();
  void _changed() {
    if (!_disposed) notifyListeners();
  }

  Future<bool> save({
    String? captureMode,
    String? audioDeviceId,
    String? txAudioDeviceId,
  }) async {
    if (_disposed || saving || applying || refreshing) return false;
    saving = true;
    error = null;
    refreshResultKey = null;
    _changed();
    try {
      await repository.setDesiredState(
        stationId,
        captureMode: captureMode,
        audioDeviceId: audioDeviceId,
        txAudioDeviceId: txAudioDeviceId,
      );
      if (_disposed) return false;
      saving = false;
      applying = true;
      _changed();
      final deadline = DateTime.now().add(const Duration(seconds: 12));
      while (!_disposed) {
        final current = readStation();
        if (current != null &&
            (captureMode == null ||
                current.desired.captureMode == captureMode) &&
            (audioDeviceId == null ||
                current.desired.audioDeviceId == audioDeviceId) &&
            (txAudioDeviceId == null ||
                current.desired.txAudioDeviceId == txAudioDeviceId)) {
          error = null;
          return true;
        }
        if (DateTime.now().isAfter(deadline) && error == null) {
          error = 'settings_sync_delayed';
          _changed();
        }
        await _delay.wait(const Duration(milliseconds: 250));
      }
    } catch (exception) {
      if (!_disposed) error = exception.toString();
    } finally {
      saving = false;
      applying = false;
      _changed();
    }
    return false;
  }

  Future<StationModel?> refresh(StationModel station) async {
    if (_disposed || saving || applying || refreshing) return null;
    refreshing = true;
    error = null;
    refreshResultKey = null;
    _changed();
    try {
      await repository.setDesiredState(stationId, refreshCapabilities: true);
      final deadline = DateTime.now().add(const Duration(seconds: 12));
      while (!_disposed && DateTime.now().isBefore(deadline)) {
        await _delay.wait(const Duration(milliseconds: 250));
        if (_disposed) return null;
        final current = readStation();
        final updated = current?.capabilities?.updatedAt;
        final previous = station.capabilities?.updatedAt;
        if (updated != null &&
            (previous == null || updated.isAfter(previous))) {
          refreshResultKey =
              current?.capabilities?.capabilityHash !=
                      station.capabilities?.capabilityHash
                  ? 'device_scan_changed'
                  : 'device_scan_unchanged';
          return current;
        }
      }
      if (!_disposed) refreshResultKey = 'device_scan_timeout';
    } catch (exception) {
      if (!_disposed) error = exception.toString();
    } finally {
      refreshing = false;
      _changed();
    }
    return null;
  }

  @override
  void dispose() {
    _disposed = true;
    _delay.close();
    super.dispose();
  }
}
