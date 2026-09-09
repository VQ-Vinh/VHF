import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:prana_mobile/domain/station/station.dart';
import 'package:prana_mobile/domain/station/station_repository.dart';
import 'package:prana_mobile/data/network/prana_api.dart';

/// Convert SDK values at the data boundary, keeping domain models SDK-free.
Object? normalizeFirestoreValue(Object? value) {
  if (value is Timestamp) return value.toDate();
  if (value is Map) {
    return value.map(
      (key, item) => MapEntry(key.toString(), normalizeFirestoreValue(item)),
    );
  }
  if (value is List) return value.map(normalizeFirestoreValue).toList();
  return value;
}

class FirestoreStationRepository implements StationRepository {
  FirestoreStationRepository(this.firestore, this.api);
  final FirebaseFirestore firestore;
  final PranaApi api;
  CollectionReference<Map<String, dynamic>> _stations(String uid) =>
      firestore.collection('users').doc(uid).collection('stations');
  StationModel _decode(DocumentSnapshot<Map<String, dynamic>> doc) =>
      StationModel.fromMap(
        doc.id,
        normalizeFirestoreValue(doc.data() ?? {}) as Map<String, dynamic>,
      );
  @override
  Stream<List<StationModel>> watchStations(String uid) => _stations(
    uid,
  ).where('active', isEqualTo: true).snapshots().map((snapshot) {
    final values = snapshot.docs.map(_decode).toList();
    values.sort((a, b) => a.name.compareTo(b.name));
    return values;
  });
  @override
  Stream<StationModel?> watchStation(String uid, String stationId) => _stations(
    uid,
  ).doc(stationId).snapshots().map((doc) => doc.exists ? _decode(doc) : null);
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
  }) => api.setDesiredState(
    stationId,
    running: running,
    targetLanguage: targetLanguage,
    captureMode: captureMode,
    audioDeviceId: audioDeviceId,
    txAudioDeviceId: txAudioDeviceId,
    refreshCapabilities: refreshCapabilities,
    retry: retry,
  );
}
