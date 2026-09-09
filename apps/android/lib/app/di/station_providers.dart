import 'package:prana_mobile/domain/station/station_repository.dart';
import 'package:prana_mobile/data/station/firestore_station_repository.dart';
import 'package:prana_mobile/app/di/auth_providers.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:prana_mobile/domain/station/station.dart';

final firestoreProvider = Provider<FirebaseFirestore>(
  (ref) => FirebaseFirestore.instance,
);

final stationClockProvider = StreamProvider<DateTime>((ref) {
  return Stream<DateTime>.periodic(
    const Duration(seconds: 1),
    (_) => DateTime.now(),
  );
});

final apiHealthProvider = StreamProvider<bool>((ref) async* {
  final api = ref.watch(apiProvider);
  var retryDelay = const Duration(seconds: 1);
  while (true) {
    final online = await api.health();
    yield online;
    if (online) {
      retryDelay = const Duration(seconds: 1);
      await Future<void>.delayed(const Duration(seconds: 5));
    } else {
      await Future<void>.delayed(retryDelay);
      retryDelay = nextRetryDelay(retryDelay);
    }
  }
});

final stationRepositoryProvider = Provider<StationRepository>(
  (ref) => FirestoreStationRepository(
    ref.watch(firestoreProvider),
    ref.watch(apiProvider),
  ),
);
final stationsProvider = StreamProvider<List<StationModel>>((ref) {
  final uid = ref.watch(authStateProvider.select((value) => value.value?.uid));
  return uid == null
      ? Stream.value(const [])
      : ref.watch(stationRepositoryProvider).watchStations(uid);
});
final stationProvider = StreamProvider.family<StationModel?, String>((
  ref,
  stationId,
) {
  final uid = ref.watch(authStateProvider.select((value) => value.value?.uid));
  return uid == null
      ? Stream.value(null)
      : ref.watch(stationRepositoryProvider).watchStation(uid, stationId);
});

Stream<T> resilientPoll<T>({
  required Future<T> Function() fetch,
  Duration pollInterval = const Duration(seconds: 2),
  Duration initialRetryDelay = const Duration(seconds: 1),
  Duration maxRetryDelay = const Duration(seconds: 5),
}) async* {
  var hasValue = false;
  var retryDelay = initialRetryDelay;
  while (true) {
    try {
      final value = await fetch();
      hasValue = true;
      retryDelay = initialRetryDelay;
      yield value;
      await Future<void>.delayed(pollInterval);
    } catch (error, stackTrace) {
      if (!hasValue) {
        yield* Stream<T>.error(error, stackTrace);
      }
      await Future<void>.delayed(retryDelay);
      retryDelay = nextRetryDelay(retryDelay, maximum: maxRetryDelay);
    }
  }
}

Duration nextRetryDelay(
  Duration current, {
  Duration maximum = const Duration(seconds: 5),
}) => Duration(
  milliseconds:
      (current.inMilliseconds * 2).clamp(1, maximum.inMilliseconds).toInt(),
);
