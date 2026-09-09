import 'package:prana_mobile/domain/station/station.dart';
import 'package:prana_mobile/domain/station/station_repository.dart';

class FakeStationRepository implements StationRepository {
  FakeStationRepository(this.station, {this.updates});
  final Stream<StationModel?>? updates;
  final StationModel station;
  final commands = <Map<String, Object?>>[];
  int watches = 0;
  @override
  Stream<StationModel?> watchStation(String uid, String stationId) async* {
    watches++;
    yield stationId == station.id
        ? station
        : StationModel.fromMap(stationId, {
          'name': stationId,
          'active': true,
          'platform': 'linux',
          'capture_state': 'idle',
          'desired_state': {'running': false},
        });
    if (updates != null) yield* updates!;
  }

  @override
  Stream<List<StationModel>> watchStations(String uid) =>
      Stream.value([station]);
  @override
  Future<void> setDesiredState(
    String stationId, {
    bool? running,
    String? targetLanguage,
    String? captureMode,
    String? audioDeviceId,
    String? txAudioDeviceId,
    bool refreshCapabilities = false,
    bool retry = false,
  }) async {
    commands.add({'station': stationId, 'running': running, 'retry': retry});
  }
}
