import 'package:prana_mobile/runtime/station/station_session.dart';
import 'package:prana_mobile/runtime/vhf/tx_controller.dart';
import 'package:prana_mobile/data/radio/tx_recorder.dart';
import 'package:prana_mobile/domain/radio/tx/tx_recorder.dart';
import 'package:prana_mobile/data/radio/api_tx_repository.dart';
import 'package:prana_mobile/domain/radio/tx/tx_repository.dart';
import 'package:prana_mobile/app/di/account_providers.dart';
import 'package:prana_mobile/app/di/station_providers.dart';
import 'package:prana_mobile/app/di/auth_providers.dart';
import 'package:prana_mobile/data/radio/flutter_speech_engine.dart';
import 'package:prana_mobile/domain/radio/source_audio_engine.dart';
import 'package:prana_mobile/domain/radio/speech_engine.dart';
import 'package:prana_mobile/domain/radio/results.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/legacy.dart';

import 'package:prana_mobile/runtime/vhf/translation_speech.dart';
import 'package:prana_mobile/data/radio/source_audio.dart';

import 'package:prana_mobile/runtime/vhf/live_controller.dart';

final speechEngineProvider = Provider<SpeechEngine>(
  (ref) => FlutterTtsSpeechEngine(),
);

final sourceAudioEngineProvider = Provider<SourceAudioEngine>((ref) {
  final engine = CachedSourceAudioEngine(ref.watch(apiProvider));
  ref.onDispose(engine.dispose);
  return engine;
});

final translationSpeechProvider =
    ChangeNotifierProvider<TranslationSpeechController>(
      (ref) => TranslationSpeechController(
        ref.watch(speechEngineProvider),
        ref.watch(sourceAudioEngineProvider),
      ),
    );

final activeSpeechStationProvider = StateProvider<String?>((ref) => null);

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
  return resilientPoll<List<TranslationResult>>(
    fetch: () async {
      final results = await api.stationLiveResults(
        key.stationId,
        timezoneOffsetMinutes: key.timezoneOffsetMinutes,
        timezone: key.timezone,
        limit: 1000,
      );
      return liveTranslationsForLocalDay(results, DateTime.now());
    },
    pollInterval: const Duration(seconds: 2),
  );
});

final txRecorderProvider = Provider<TxRecorder Function()>(
  (ref) => PhoneTxRecorder.new,
);
final txRepositoryProvider = Provider<TxRepository Function()>((ref) {
  final api = ref.watch(apiProvider);
  final storage = ref.watch(secureStorageProvider);
  final uid =
      ref.watch(authStateProvider.select((value) => value.value?.uid)) ?? '';
  return () => ApiTxRepository(api, storage: storage, identityScope: uid);
});
final stationSessionProvider = ChangeNotifierProvider.autoDispose
    .family<StationSession, String>((ref, stationId) {
      final uid =
          ref.watch(authStateProvider.select((value) => value.value?.uid)) ??
          '';
      final repository = ref.watch(stationRepositoryProvider);
      final session = StationSession(
        uid: uid,
        stationId: stationId,
        rx: LiveUxController(
          stationId: stationId,
          send:
              ({running, targetLanguage, retry = false}) =>
                  repository.setDesiredState(
                    stationId,
                    running: running,
                    targetLanguage: targetLanguage,
                    retry: retry,
                  ),
        ),
        tx: TxController(
          stationId: stationId,
          repository: ref.watch(txRepositoryProvider)(),
          recorder: ref.watch(txRecorderProvider)(),
        ),
      );
      void sync() {
        final station = ref.read(stationProvider(stationId)).value;
        if (station == null || !station.active) return;
        session.synchronize(
          station,
          ref.read(stationClockProvider).value ?? DateTime.now(),
          ref.read(planEntitlementsProvider),
          ref.read(apiHealthProvider).value ?? false,
        );
      }

      ref.listen(stationProvider(stationId), (_, _) => sync());
      ref.listen(stationClockProvider, (_, _) => sync());
      ref.listen(planEntitlementsProvider, (_, _) => sync());
      ref.listen(apiHealthProvider, (_, _) => sync());
      sync();
      return session;
    });
final liveUxControllerProvider = Provider.autoDispose
    .family<LiveUxController, String>(
      (ref, stationId) => ref.watch(stationSessionProvider(stationId)).rx,
    );
