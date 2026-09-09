import 'station.dart';

abstract interface class StationRepository {
  Stream<List<StationModel>> watchStations(String uid);
  Stream<StationModel?> watchStation(String uid, String stationId);
  Future<void> setDesiredState(
    String stationId, {
    bool? running,
    String? targetLanguage,
    String? captureMode,
    String? audioDeviceId,
    String? txAudioDeviceId,
    bool refreshCapabilities = false,
    bool retry = false,
  });
}
