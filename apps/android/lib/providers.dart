import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'models/station.dart';
import 'services/prana_api.dart';

final authProvider = Provider<FirebaseAuth>((ref) => FirebaseAuth.instance);
final firestoreProvider = Provider<FirebaseFirestore>(
  (ref) => FirebaseFirestore.instance,
);
final apiProvider = Provider<PranaApi>(
  (ref) => PranaApi(ref.watch(authProvider)),
);
final secureStorageProvider = Provider<FlutterSecureStorage>(
  (ref) => const FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  ),
);

final authStateProvider = StreamProvider<User?>((ref) {
  return ref.watch(authProvider).authStateChanges();
});

final stationClockProvider = StreamProvider<DateTime>((ref) {
  return Stream<DateTime>.periodic(
    const Duration(seconds: 1),
    (_) => DateTime.now(),
  );
});

final stationsProvider = StreamProvider<List<StationModel>>((ref) {
  final user = ref.watch(authStateProvider).value;
  if (user == null) return const Stream.empty();
  return ref
      .watch(firestoreProvider)
      .collection('users')
      .doc(user.uid)
      .collection('stations')
      .where('active', isEqualTo: true)
      .snapshots()
      .map((snapshot) {
        final stations = snapshot.docs.map(StationModel.fromDocument).toList();
        stations.sort((a, b) => a.name.compareTo(b.name));
        return stations;
      });
});

final stationProvider = StreamProvider.family<StationModel?, String>((
  ref,
  stationId,
) {
  final user = ref.watch(authStateProvider).value;
  if (user == null) return Stream.value(null);
  return ref
      .watch(firestoreProvider)
      .collection('users')
      .doc(user.uid)
      .collection('stations')
      .doc(stationId)
      .snapshots()
      .map((doc) => doc.exists ? StationModel.fromDocument(doc) : null);
});

final liveResultsProvider = StreamProvider.family<
  List<TranslationResult>,
  ({String stationId, String sessionId})
>((ref, key) {
  final user = ref.watch(authStateProvider).value;
  if (user == null || key.sessionId.isEmpty) return Stream.value(const []);
  return ref
      .watch(firestoreProvider)
      .collection('users')
      .doc(user.uid)
      .collection('stations')
      .doc(key.stationId)
      .collection('sessions')
      .doc(key.sessionId)
      .collection('results')
      .orderBy('sequence', descending: true)
      .limit(100)
      .snapshots()
      .map(
        (snapshot) =>
            snapshot.docs
                .map(TranslationResult.fromDocument)
                .fold(<String, TranslationResult>{}, (items, result) {
                  items[result.requestId] = result;
                  return items;
                })
                .values
                .toList(),
      );
});

final accountProvider = FutureProvider<Map<String, dynamic>>((ref) {
  ref.watch(authStateProvider);
  return ref.watch(apiProvider).account();
});
