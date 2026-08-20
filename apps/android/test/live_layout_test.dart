import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/core/localization.dart';
import 'package:prana_mobile/core/theme.dart';
import 'package:prana_mobile/features/live/live_controller.dart';
import 'package:prana_mobile/features/live/live_screen.dart';
import 'package:prana_mobile/models/station.dart';
import 'package:prana_mobile/providers.dart';
import 'package:prana_mobile/services/source_audio.dart';
import 'package:prana_mobile/services/translation_speech.dart';

class _NoopSpeechEngine implements SpeechEngine {
  int stopCalls = 0;

  @override
  Future<String?> resolveLocale(String preferredLocale) async =>
      preferredLocale;

  @override
  Future<void> speak(String text, String locale) async {}

  @override
  Future<void> stop() async {
    stopCalls++;
  }
}

class _NoopSourceAudioEngine implements SourceAudioEngine {
  int stopCalls = 0;

  @override
  Future<void> clearCache() async {}

  @override
  Future<void> play(
    String stationId,
    String sessionId,
    String requestId,
  ) async {}

  @override
  Future<void> stop() async {
    stopCalls++;
  }
}

void main() {
  StationModel station({
    String name = 'VINH',
    bool running = true,
    int desiredGeneration = 1,
    int observedGeneration = 1,
    int commandFailedGeneration = 0,
    String? commandError,
  }) => StationModel(
    id: 'station-1',
    name: name,
    platform: 'windows',
    active: true,
    captureState: running ? 'listening' : 'idle',
    desired: DesiredState(
      running: running,
      targetLanguage: 'vi',
      retryGeneration: 0,
      generation: desiredGeneration,
    ),
    observedGeneration: observedGeneration,
    commandFailedGeneration: commandFailedGeneration,
    commandError: commandError,
    sessionId: 'session-1',
    sequence: 2,
    lastSeenAt: DateTime.now(),
  );

  Widget harness({
    required Size size,
    required Widget child,
    double textScale = 1,
    Locale locale = const Locale('en'),
  }) => MaterialApp(
    theme: PranaTheme.light(),
    locale: locale,
    supportedLocales: AppText.supportedLocales,
    localizationsDelegates: const [
      GlobalMaterialLocalizations.delegate,
      GlobalWidgetsLocalizations.delegate,
      GlobalCupertinoLocalizations.delegate,
    ],
    builder:
        (context, appChild) => MediaQuery(
          data: MediaQueryData(
            size: size,
            textScaler: TextScaler.linear(textScale),
          ),
          child: appChild!,
        ),
    home: child,
  );

  testWidgets('live audio toggle sits beside history and stops auto playback', (
    tester,
  ) async {
    final speechEngine = _NoopSpeechEngine();
    final sourceAudio = _NoopSourceAudioEngine();
    final controller = TranslationSpeechController(speechEngine, sourceAudio);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          translationSpeechProvider.overrideWith((ref) => controller),
        ],
        child: harness(
          size: const Size(360, 800),
          child: Scaffold(
            body: LiveFeedHeader(onHistory: () {}),
          ),
        ),
      ),
    );

    // The plan-usage badge is gone now that only the newest result shows.
    expect(find.textContaining(RegExp(r'\d+/\d+')), findsNothing);
    expect(find.byIcon(Icons.volume_up_outlined), findsOneWidget);
    expect(find.byIcon(Icons.history), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('live-audio-toggle')));
    await tester.pump();

    expect(find.byIcon(Icons.volume_off_outlined), findsOneWidget);
    expect(controller.autoPlaybackEnabled, isFalse);
    expect(speechEngine.stopCalls, 1);
    expect(sourceAudio.stopCalls, 1);
  });

  testWidgets('live header stays compact on a 360dp screen', (tester) async {
    tester.view.physicalSize = const Size(360, 800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      harness(
        size: const Size(360, 800),
        textScale: 1.3,
        child: Scaffold(
          appBar: LiveHeader(
            station: station(
              name: 'VINH STATION WITH A VERY LONG TECHNICAL NAME',
            ),
            online: true,
            ux: const LiveUxState(),
            onToggle: () {},
            onSettings: () {},
          ),
        ),
      ),
    );

    expect(find.byKey(const ValueKey('live-header')), findsOneWidget);
    expect(find.text('LIVE TRANSLATION'), findsNothing);
    expect(find.textContaining('RX LISTENING'), findsOneWidget);
    expect(find.byIcon(Icons.settings_outlined), findsOneWidget);
    expect(
      tester.getSize(find.byKey(const ValueKey('live-header'))).height,
      64,
    );
    expect(tester.takeException(), isNull);
  });

  testWidgets('live header clearly presents a pending start command', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(360, 800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      harness(
        size: const Size(360, 800),
        locale: const Locale('vi'),
        child: Scaffold(
          appBar: LiveHeader(
            station: station(running: false),
            online: true,
            ux: const LiveUxState(
              phase: LiveCommandPhase.awaitingStation,
              pendingRunning: true,
            ),
            onToggle: null,
            onSettings: () {},
          ),
        ),
      ),
    );

    expect(find.byKey(const ValueKey('live-toggle-progress')), findsOneWidget);
    expect(find.text('Đang bật…'), findsOneWidget);
    expect(find.text('RX STARTING'), findsOneWidget);
    expect(
      tester.getSize(find.byKey(const ValueKey('live-toggle-button'))),
      const Size(118, 40),
    );
    expect(
      tester.getRect(find.byKey(const ValueKey('live-toggle-label'))).right,
      lessThanOrEqualTo(
        tester.getRect(find.byKey(const ValueKey('live-toggle-button'))).right,
      ),
    );
    final progress = tester.widget<CircularProgressIndicator>(
      find.byType(CircularProgressIndicator),
    );
    expect(progress.strokeWidth, 2.6);
    expect(tester.takeException(), isNull);
  });

  testWidgets('live header clearly presents a pending stop command', (
    tester,
  ) async {
    await tester.pumpWidget(
      harness(
        size: const Size(412, 915),
        child: Scaffold(
          appBar: LiveHeader(
            station: station(),
            online: true,
            ux: const LiveUxState(
              phase: LiveCommandPhase.awaitingStation,
              pendingRunning: false,
            ),
            onToggle: null,
            onSettings: () {},
          ),
        ),
      ),
    );

    expect(find.text('Stopping…'), findsOneWidget);
    expect(find.text('RX STOPPING'), findsOneWidget);
    expect(find.byKey(const ValueKey('live-toggle-progress')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('an offline Station stops the header spinning forever', (
    tester,
  ) async {
    // Generation 2 was never observed: exactly the state a Station leaves
    // behind when it drops out mid-command.
    await tester.pumpWidget(
      harness(
        size: const Size(412, 915),
        child: Scaffold(
          appBar: LiveHeader(
            station: station(
              running: false,
              desiredGeneration: 2,
              observedGeneration: 1,
            ),
            online: false,
            ux: const LiveUxState(phase: LiveCommandPhase.offline),
            onToggle: null,
            onSettings: () {},
          ),
        ),
      ),
    );

    expect(find.byKey(const ValueKey('live-toggle-progress')), findsNothing);
    expect(find.text('Stopping…'), findsNothing);
    expect(find.text('RX OFF'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  test('offline leaves no pending command behind', () {
    final subject = LiveUxController(
      stationId: 'station-1',
      send: ({running, targetLanguage, retry = false}) async {},
    );
    addTearDown(subject.dispose);
    final pending = station(desiredGeneration: 2, observedGeneration: 1);
    subject.setRunning(pending, false);

    subject.synchronize(pending, online: false);

    expect(subject.state.phase, LiveCommandPhase.offline);
    expect(subject.state.pendingRunning, isNull);
  });

  test('header and dock share the transition state until command applies', () {
    final listeningStation = station(running: true);
    const starting = LiveUxState(
      phase: LiveCommandPhase.awaitingStation,
      pendingRunning: true,
    );

    expect(
      liveStationDisplayState(
        station: listeningStation,
        online: true,
        ux: starting,
      ),
      'STARTING',
    );
    expect(
      liveStationDisplayState(
        station: listeningStation,
        online: true,
        ux: const LiveUxState(),
      ),
      'LISTENING',
    );
  });

  test('command failure takes precedence over pending START', () {
    final failedStation = station(
      desiredGeneration: 2,
      observedGeneration: 1,
      commandFailedGeneration: 2,
      commandError: 'AUDIO_INPUT_DEVICE_NOT_FOUND',
    );

    expect(
      liveStationDisplayState(
        station: failedStation,
        online: true,
        ux: const LiveUxState(
          phase: LiveCommandPhase.failed,
          error: 'rx_audio_input_not_found',
        ),
      ),
      'ERROR',
    );
  });

  testWidgets('input and output language fields have equal geometry', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(412, 915);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      harness(
        size: const Size(412, 915),
        textScale: 1.3,
        child: Scaffold(
          body: LanguageStrip(
            detectedLanguage: 'a-very-long-detected-language',
            targetLanguage: 'vi',
            enabled: true,
            onChanged: (_) {},
          ),
        ),
      ),
    );

    final input = tester.getSize(
      find.byKey(const ValueKey('input-language-field')),
    );
    final output = tester.getSize(
      find.byKey(const ValueKey('output-language-field')),
    );

    expect(input.width, output.width);
    expect(input.height, output.height);
    expect(input.height, lessThanOrEqualTo(60));
    final stripCenter =
        tester.getCenter(find.byKey(const ValueKey('rx-language-strip'))).dx;
    final arrowCenter =
        tester.getCenter(find.byKey(const ValueKey('rx-language-arrow'))).dx;
    expect(arrowCenter, closeTo(stripCenter, .1));
    expect(tester.takeException(), isNull);
  });
}
