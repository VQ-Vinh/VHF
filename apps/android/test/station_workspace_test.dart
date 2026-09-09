import 'package:prana_mobile/l10n/app_localizations.dart';
import 'package:prana_mobile/features/station/history/history_screen.dart';
import 'package:prana_mobile/domain/radio/tx/tx_phase.dart';
import 'package:prana_mobile/app/di/telemetry_providers.dart';
import 'dashboard_test.dart' show TestTelemetry;
import 'dart:async';
import 'dart:typed_data';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:prana_mobile/app/di/auth_providers.dart';
import 'package:prana_mobile/app/di/account_providers.dart';
import 'package:prana_mobile/app/di/history_providers.dart';
import 'package:prana_mobile/app/di/radio_providers.dart';
import 'package:prana_mobile/app/di/station_providers.dart';
import 'package:prana_mobile/core/theme.dart';
import 'package:prana_mobile/domain/station/station.dart';
import 'package:prana_mobile/domain/radio/history_repository.dart';
import 'package:prana_mobile/domain/radio/results.dart';
import 'package:prana_mobile/domain/radio/tx/tx_draft.dart';
import 'package:prana_mobile/domain/radio/speech_engine.dart';
import 'package:prana_mobile/domain/radio/source_audio_engine.dart';
import 'package:prana_mobile/features/station/workspace/station_workspace_screen.dart';
import 'package:prana_mobile/features/station/workspace/station_tab.dart';
import 'package:prana_mobile/runtime/station/station_runtime_host.dart';
import 'support/fake_station_repository.dart';
import 'support/fake_tx_repository.dart';
import 'support/test_recorder.dart';

class _User extends Fake implements User {
  @override
  String get uid => identity;
  _User([this.identity = 'owner']);
  final String identity;
}

class _Speech implements SpeechEngine {
  final spoken = <String>[];
  @override
  Future<String?> resolveLocale(String locale) async => locale;
  @override
  Future<void> speak(String text, String locale) async {
    spoken.add(text);
  }

  @override
  Future<void> stop() async {}
}

class _Audio implements SourceAudioEngine {
  @override
  Future<void> play(String station, String session, String request) async {}
  @override
  Future<void> stop() async {}
  @override
  Future<void> clearCache() async {}
}

class _History implements HistoryRepository {
  @override
  Future<List<StationHistoryDay>> days(
    String stationId, {
    required bool tx,
    required int offset,
    String? timezone,
  }) async => [];
  @override
  Future<List<TranslationResult>> rxResults(
    String stationId,
    String date, {
    required int offset,
    String? timezone,
  }) async => [];
  @override
  Future<List<TxDraft>> txJobs(
    String stationId,
    String date, {
    required int offset,
    String? timezone,
  }) async => [];
  @override
  Future<Uint8List> txAudio(String stationId, String jobId) async =>
      Uint8List(0);
}

void main() {
  for (final (running, initialPage) in [
    (false, 'dashboard'),
    (true, 'dashboard'),
    (false, 'control'),
    (false, 'history'),
    (false, 'settings'),
  ]) {
    testWidgets(
      'workspace retains runtime across pages, running=$running initial=$initialPage',
      (tester) async {
        final previousErrorHandler = FlutterError.onError;
        FlutterError.onError = (details) {
          debugPrint(details.toString());
          previousErrorHandler?.call(details);
        };
        addTearDown(() => FlutterError.onError = previousErrorHandler);
        tester.view.physicalSize = const Size(1024, 768);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        tester.platformDispatcher.localesTestValue = const [Locale('en')];
        addTearDown(tester.platformDispatcher.clearLocalesTestValue);
        addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
        FlutterSecureStorage.setMockInitialValues({});
        final authChanges = StreamController<User?>.broadcast();
        final now = DateTime.now();
        final station = StationModel(
          id: 's',
          name: 'PRANA Station',
          platform: 'linux',
          active: true,
          captureState: running ? 'listening' : 'idle',
          desired: DesiredState(
            running: running,
            targetLanguage: 'vi',
            retryGeneration: 0,
            generation: 7,
          ),
          observedGeneration: 7,
          sessionId: 'existing-session',
          sequence: 4,
          lastSeenAt: now,
          capabilities: const StationCapabilities(
            capabilityHash: 'test',
            captureModes: ['device', 'loopback'],
            audioDevices: [],
            storagePath: '',
          ),
        );
        final projectionChanges = StreamController<StationModel?>.broadcast();
        final repository = FakeStationRepository(
          station,
          updates: projectionChanges.stream,
        );
        final recorder = TestRecorder();
        var recorderCreations = 0;
        final telemetry = TestTelemetry();
        final txRepository = FakeTxRepository(processingDelay: Duration.zero);
        final speech = _Speech();
        final results = StreamController<List<TranslationResult>>.broadcast();
        final router = GoRouter(
          initialLocation: '/stations/s/$initialPage',
          routes: [
            GoRoute(
              path: '/stations',
              builder: (_, _) => const Scaffold(body: Text('Station list')),
            ),
            GoRoute(
              path: '/stations/:id/:tab',
              pageBuilder:
                  (_, state) => MaterialPage<void>(
                    key: const ValueKey('workspace-s'),
                    child: StationWorkspaceScreen(
                      stationId: state.pathParameters['id']!,
                      page: StationPage.fromPath(state.pathParameters['tab']),
                    ),
                  ),
            ),
          ],
        );
        await tester.pumpWidget(
          ProviderScope(
            overrides: [
              authStateProvider.overrideWith((ref) async* {
                yield _User();
                yield* authChanges.stream;
              }),
              stationRepositoryProvider.overrideWithValue(repository),
              txRepositoryProvider.overrideWithValue(() => txRepository),
              txRecorderProvider.overrideWithValue(
                () => recorderCreations++ == 0 ? recorder : TestRecorder(),
              ),
              accountProvider.overrideWith((ref) async => <String, dynamic>{}),
              apiHealthProvider.overrideWith((ref) => Stream.value(true)),
              stationClockProvider.overrideWith((ref) => Stream.value(now)),
              liveResultsProvider.overrideWith((ref, key) => results.stream),
              speechEngineProvider.overrideWithValue(speech),
              sourceAudioEngineProvider.overrideWithValue(_Audio()),
              historyRepositoryProvider.overrideWithValue(_History()),
              telemetryRepositoryProvider.overrideWithValue(telemetry),
            ],
            child: MaterialApp.router(
              theme: PranaTheme.light(),

              supportedLocales: AppLocalizations.supportedLocales,
              localizationsDelegates: const [
                AppLocalizations.delegate,
                GlobalMaterialLocalizations.delegate,
                GlobalWidgetsLocalizations.delegate,
                GlobalCupertinoLocalizations.delegate,
              ],
              builder: (_, child) => StationRuntimeHost(child: child!),
              routerConfig: router,
            ),
          ),
        );
        for (var i = 0; i < 5; i++) {
          await tester.pump(const Duration(milliseconds: 100));
        }
        final container = ProviderScope.containerOf(
          tester.element(find.byType(StationWorkspaceScreen)),
        );
        final session = container.read(stationSessionProvider('s'));
        Future<void> settlePage() async {
          for (var i = 0; i < 4; i++) {
            await tester.pump(const Duration(milliseconds: 100));
          }
        }

        Future<void> backPage() async {
          await tester.tap(find.byKey(const ValueKey('workspace-back')));
          await settlePage();
        }

        Future<void> openPage(String page) async {
          while (find
              .byKey(const ValueKey('station-tab-dashboard'))
              .evaluate()
              .isEmpty) {
            await backPage();
          }
          if (page == 'history') {
            await tester.tap(find.byKey(const ValueKey('station-tab-live')));
            await settlePage();
          }
          final finder = find.byKey(
            ValueKey(switch (page) {
              'history' => 'live-history-button',
              'settings' => 'station-settings-button',
              _ => 'station-tab-$page',
            }),
          );
          await tester.ensureVisible(finder);
          await tester.tap(finder);
          await settlePage();
        }

        if (initialPage != 'dashboard' && initialPage != 'control') {
          expect(
            find.byKey(const ValueKey('station-tab-dashboard')),
            findsNothing,
          );
          await backPage();
          expect(
            router.routeInformationProvider.value.uri.path,
            initialPage == 'history'
                ? '/stations/s/live'
                : '/stations/s/dashboard',
          );
        }
        await openPage('dashboard');
        expect(
          find.byKey(const ValueKey('station-tab-dashboard')),
          findsOneWidget,
        );
        expect(
          find.byKey(const ValueKey('station-tab-control')),
          findsOneWidget,
        );
        expect(find.byKey(const ValueKey('station-tab-live')), findsOneWidget);
        expect(find.byKey(const ValueKey('station-tab-history')), findsNothing);
        expect(
          find.byKey(const ValueKey('station-tab-settings')),
          findsNothing,
        );
        expect(find.byIcon(Icons.settings_outlined), findsOneWidget);
        await openPage('settings');
        expect(
          find.byKey(const ValueKey('station-tab-dashboard')),
          findsNothing,
        );
        await backPage();
        expect(
          router.routeInformationProvider.value.uri.path,
          '/stations/s/dashboard',
        );
        await openPage('control');
        await tester.ensureVisible(
          find.byKey(const ValueKey('steering-right')),
        );
        await tester.tap(find.byKey(const ValueKey('steering-right')));
        await tester.pump();
        expect(
          tester
              .widget<Text>(find.byKey(const ValueKey('steering-angle')))
              .data,
          contains('5°'),
        );
        await openPage('settings');
        await backPage();
        expect(
          router.routeInformationProvider.value.uri.path,
          '/stations/s/control',
        );
        expect(
          tester
              .widget<Text>(find.byKey(const ValueKey('steering-angle')))
              .data,
          contains('5°'),
        );
        await openPage('live');
        expect(find.byIcon(Icons.settings_outlined), findsOneWidget);
        await openPage('settings');
        await backPage();
        expect(
          router.routeInformationProvider.value.uri.path,
          '/stations/s/live',
        );
        await openPage('dashboard');

        results.add([]);
        await tester.pump();
        await tester.pump();
        await tester.pump();
        results.add([
          TranslationResult(
            requestId: 'r',
            sessionId: 'existing-session',
            sequence: 5,
            transcript: 'Hello',
            translation: 'New RX result',
            language: 'en',
            targetLanguage: 'vi',
            confidence: 1,
            timestamp: now,
          ),
        ]);
        await tester.pump();
        await tester.pump();
        expect(speech.spoken, ['New RX result']);
        for (final tab in [
          'live',
          'dashboard',
          'history',
          'settings',
          'live',
        ]) {
          await openPage(tab);
          for (var i = 0; i < 4; i++) {
            await tester.pump(const Duration(milliseconds: 100));
          }
          expect(
            identical(container.read(stationSessionProvider('s')), session),
            true,
          );
          expect(tester.takeException(), isNull);
        }
        await openPage('history');
        await tester.tap(find.text('TX'));
        await settlePage();
        final historyState = tester.state<HistoryScreenState>(
          find.byType(HistoryScreen),
        );
        expect(historyState.mode, HistoryMode.tx);
        await openPage('settings');
        await backPage();
        expect(
          router.routeInformationProvider.value.uri.path,
          '/stations/s/live',
        );
        await openPage('history');
        expect(tester.state(find.byType(HistoryScreen)), same(historyState));
        expect(historyState.mode, HistoryMode.tx);
        await backPage();
        if (!running) {
          await openPage('settings');
          final mode = find.byType(SegmentedButton<String>);
          expect(
            tester.widget<SegmentedButton<String>>(mode).onSelectionChanged,
            isNotNull,
          );
          await tester.tap(find.text('LOOPBACK'));
          await settlePage();
          expect(tester.widget<SegmentedButton<String>>(mode).selected, {
            'loopback',
          });
          await backPage();
          await openPage('settings');
          expect(tester.widget<SegmentedButton<String>>(mode).selected, {
            'loopback',
          });
          await backPage();
        }
        expect(telemetry.watches, 1);
        if (running) {
          session.tx.startRecording();
          await tester.pump(const Duration(milliseconds: 200));
          await tester.tap(find.byKey(const ValueKey('station-tab-dashboard')));
          for (var i = 0; i < 5; i++) {
            await tester.pump(const Duration(milliseconds: 100));
          }
          expect(recorder.stops, 1);
          expect(session.tx.state.phase, TxPhase.reviewReady);
          expect(find.byKey(const ValueKey('tx-review-view')), findsNothing);
          expect(txRepository.lastConfirmedTranslation, isNull);
          await openPage('live');
          for (var i = 0; i < 5; i++) {
            await tester.pump(const Duration(milliseconds: 100));
          }
          expect(find.byKey(const ValueKey('tx-review-view')), findsOneWidget);
          await tester.enterText(
            find.byKey(const ValueKey('tx-translation-editor')),
            'Edited translation',
          );
          Navigator.of(
            tester.element(find.byKey(const ValueKey('tx-review-view'))),
          ).pop();
          for (var i = 0; i < 4; i++) {
            await tester.pump(const Duration(milliseconds: 100));
          }
          await openPage('settings');
          await tester.pump(const Duration(milliseconds: 200));
          await openPage('live');
          for (var i = 0; i < 4; i++) {
            await tester.pump(const Duration(milliseconds: 100));
          }
          expect(find.byKey(const ValueKey('tx-review-view')), findsNothing);
          await tester.tap(find.byKey(const ValueKey('tx-open-review')));
          for (var i = 0; i < 4; i++) {
            await tester.pump(const Duration(milliseconds: 100));
          }
          expect(
            tester
                .widget<TextField>(
                  find.byKey(const ValueKey('tx-translation-editor')),
                )
                .controller!
                .text,
            'Edited translation',
          );
          Navigator.of(
            tester.element(find.byKey(const ValueKey('tx-review-view'))),
          ).pop();
          await tester.pump(const Duration(milliseconds: 400));
          final confirming = session.tx.confirmTransmission(
            'Edited translation',
          );
          await session.tx.confirmTransmission('Duplicate');
          await tester.tap(find.byKey(const ValueKey('station-tab-dashboard')));
          await tester.pump(const Duration(milliseconds: 100));
          expect(session.tx.state.phase, TxPhase.processing);
          await tester.pump(const Duration(milliseconds: 900));
          expect(session.tx.state.phase, TxPhase.queued);
          await tester.pump(const Duration(seconds: 1));
          expect(session.tx.state.phase, TxPhase.transmitting);
          await tester.pump(const Duration(seconds: 1));
          await confirming;
          expect(session.tx.state.phase, TxPhase.completed);
          expect(txRepository.lastConfirmedTranslation, 'Edited translation');
        }
        if (!running && initialPage == 'dashboard') {
          for (final size in [
            const Size(320, 800),
            const Size(375, 800),
            const Size(390, 800),
            const Size(400, 800),
            const Size(430, 800),
            const Size(768, 1024),
            const Size(768, 320),
            const Size(360, 800),
            const Size(800, 360),
            const Size(1024, 768),
            const Size(1280, 800),
            const Size(1440, 900),
            const Size(1920, 1080),
          ]) {
            for (final scale in [1.0, 1.5, 2.0]) {
              for (final locale in ['vi', 'en']) {
                tester.view.physicalSize = size;
                tester.platformDispatcher.textScaleFactorTestValue = scale;
                tester.platformDispatcher.localesTestValue = [Locale(locale)];
                await tester.pump();
                await tester.pump();
                expect(
                  tester.takeException(),
                  isNull,
                  reason: '$size / $scale / $locale',
                );
                for (final tab in [
                  'dashboard',
                  'control',
                  'live',
                  'history',
                  'settings',
                ]) {
                  await openPage(tab);
                  await tester.pump(const Duration(milliseconds: 200));
                  await tester.pump();
                  expect(
                    tester.takeException(),
                    isNull,
                    reason: '$tab / $size / $scale / $locale',
                  );
                }
              }
            }
          }
        }
        expect(repository.commands, isEmpty);
        expect(repository.watches, 1);
        expect(session.state.station?.sessionId, 'existing-session');
        expect(session.state.station?.desired.generation, 7);
        expect(recorder.disposals, 0);
        expect(speech.spoken, ['New RX result']);
        tester.view.physicalSize = const Size(1024, 768);
        tester.platformDispatcher.textScaleFactorTestValue = 1;
        tester.platformDispatcher.localesTestValue = const [Locale('en')];
        await tester.pump();
        await openPage('dashboard');
        await tester.tap(find.byKey(const ValueKey('workspace-back')));
        for (var i = 0; i < 5; i++) {
          await tester.pump(const Duration(milliseconds: 100));
        }
        expect(find.text('Station list'), findsOneWidget);
        expect(
          identical(container.read(stationSessionProvider('s')), session),
          true,
        );
        for (var i = 0; i < 10; i++) {
          await tester.pump(const Duration(milliseconds: 100));
        }
        expect(
          find.byType(StationWorkspaceScreen, skipOffstage: false),
          findsNothing,
        );
        expect(telemetry.stream.hasListener, false);
        expect(recorder.disposals, 0);
        results.add([
          TranslationResult(
            requestId: 'after-back',
            sessionId: 'existing-session',
            sequence: 6,
            transcript: 'Hello again',
            translation: 'Audio after Back',
            language: 'en',
            targetLanguage: 'vi',
            confidence: 1,
            timestamp: now,
          ),
        ]);
        for (var i = 0; i < 4; i++) {
          await tester.pump();
        }
        expect(speech.spoken.last, 'Audio after Back');
        if (!running) {
          container.read(activeSpeechStationProvider.notifier).state =
              'second-station';
          for (var i = 0; i < 10; i++) {
            await tester.pump();
          }
          final second = container.read(
            stationSessionProvider('second-station'),
          );
          expect(second.stationId, 'second-station');
          expect(second.uid, 'owner');
          expect(identical(second, session), false);
          expect(recorder.disposals, 1);
          projectionChanges.add(null);
          for (var i = 0; i < 10; i++) {
            await tester.pump();
          }
          expect(container.read(activeSpeechStationProvider), isNull);
        }
        authChanges.add(_User('other-user'));
        for (var i = 0; i < 5; i++) {
          await tester.pump();
        }
        expect(container.read(activeSpeechStationProvider), isNull);
        expect(recorder.disposals, 1);
        authChanges.add(null);
        for (var i = 0; i < 5; i++) {
          await tester.pump();
        }
        expect(container.read(activeSpeechStationProvider), isNull);
        expect(repository.commands, isEmpty);
        await tester.pumpWidget(const SizedBox.shrink());
        router.dispose();
        await projectionChanges.close();
        await authChanges.close();
        await results.close();
        await telemetry.stream.close();
      },
    );
  }
}
