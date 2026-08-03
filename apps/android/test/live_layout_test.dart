import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/core/localization.dart';
import 'package:prana_mobile/core/theme.dart';
import 'package:prana_mobile/features/live/live_controller.dart';
import 'package:prana_mobile/features/live/live_screen.dart';
import 'package:prana_mobile/models/station.dart';

void main() {
  StationModel station({String name = 'VINH', bool running = true}) =>
      StationModel(
        id: 'station-1',
        name: name,
        platform: 'windows',
        active: true,
        captureState: running ? 'listening' : 'idle',
        desired: DesiredState(
          running: running,
          targetLanguage: 'vi',
          retryGeneration: 0,
          generation: 1,
        ),
        observedGeneration: 1,
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
