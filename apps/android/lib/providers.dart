import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/legacy.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:google_sign_in/google_sign_in.dart';

import 'models/station.dart';
import 'models/plan_entitlements.dart';
import 'services/prana_api.dart';
import 'services/authentication_service.dart';
import 'services/translation_speech.dart';
import 'services/source_audio.dart';
import 'core/localization.dart';
import 'core/user_region.dart';

final authProvider = Provider<FirebaseAuth>((ref) => FirebaseAuth.instance);
final authenticationServiceProvider = Provider<AuthenticationService>(
  (ref) => FirebaseAuthenticationService(
    ref.watch(authProvider),
    GoogleSignIn.instance,
  ),
);
final firestoreProvider = Provider<FirebaseFirestore>(
  (ref) => FirebaseFirestore.instance,
);
final apiProvider = Provider<PranaApi>(
  (ref) => PranaApi(ref.watch(authProvider)),
);
final secureStorageProvider = Provider<FlutterSecureStorage>(
  (ref) => const FlutterSecureStorage(aOptions: AndroidOptions()),
);
final speechEngineProvider = Provider<SpeechEngine>(
  (ref) => FlutterTtsSpeechEngine(),
);
final sourceAudioEngineProvider = Provider<SourceAudioEngine>(
  (ref) => CachedSourceAudioEngine(ref.watch(apiProvider)),
);
final translationSpeechProvider =
    ChangeNotifierProvider<TranslationSpeechController>(
      (ref) => TranslationSpeechController(
        ref.watch(speechEngineProvider),
        ref.watch(sourceAudioEngineProvider),
      ),
    );
final activeSpeechStationProvider = StateProvider<String?>((ref) => null);

final appLocaleProvider = ChangeNotifierProvider<AppLocaleController>(
  (ref) => AppLocaleController(ref.watch(secureStorageProvider)),
);

final userRegionProvider = ChangeNotifierProvider<UserRegionController>(
  (ref) => UserRegionController(ref.watch(secureStorageProvider)),
);

final countriesProvider = FutureProvider<List<CountryOption>>((ref) async {
  final values = await ref.watch(apiProvider).countries();
  return values.map(CountryOption.fromJson).toList();
});

final authStateProvider = StreamProvider<User?>((ref) {
  return ref.watch(authProvider).userChanges();
});

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
      retryDelay = _nextRetryDelay(retryDelay);
    }
  }
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

final liveResultsProvider = StreamProvider.autoDispose.family<
  List<TranslationResult>,
  ({
    String stationId,
    String localDate,
    int timezoneOffsetMinutes,
    String? timezone,
  })
>((ref, key) {
  final user = ref.watch(authStateProvider).value;
  if (user == null) return Stream.value(const []);
  final api = ref.watch(apiProvider);
  final limit = ref.watch(planEntitlementsProvider).liveLogLimit;
  return resilientPoll<List<TranslationResult>>(
    fetch: () async {
      final results = await api.stationLiveResults(
        key.stationId,
        timezoneOffsetMinutes: key.timezoneOffsetMinutes,
        timezone: key.timezone,
        limit: limit <= 0 ? 1000 : limit,
      );
      return liveTranslationsForLocalDay(results, DateTime.now());
    },
    pollInterval: const Duration(seconds: 2),
  );
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
      retryDelay = _nextRetryDelay(retryDelay, maximum: maxRetryDelay);
    }
  }
}

Duration _nextRetryDelay(
  Duration current, {
  Duration maximum = const Duration(seconds: 5),
}) => Duration(
  milliseconds:
      (current.inMilliseconds * 2).clamp(1, maximum.inMilliseconds).toInt(),
);

final accountProvider = FutureProvider<Map<String, dynamic>>((ref) {
  final user = ref.watch(authStateProvider).value;
  if (user == null) return const <String, dynamic>{};
  return ref.watch(apiProvider).account();
});

final planEntitlementsProvider = Provider<PlanEntitlements>((ref) {
  final account = ref.watch(accountProvider).value ?? const {};
  return PlanEntitlements.fromAccount(account);
});
