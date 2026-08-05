import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/core/localization.dart';
import 'package:prana_mobile/core/theme.dart';
import 'package:prana_mobile/features/live/live_controller.dart';
import 'package:prana_mobile/features/live/live_screen.dart';
import 'package:prana_mobile/features/tx/application/fake_tx_repository.dart';
import 'package:prana_mobile/features/tx/application/tx_controller.dart';
import 'package:prana_mobile/features/tx/domain/tx_phase.dart';
import 'package:prana_mobile/features/tx/presentation/widgets/tx_live_dock.dart';
import 'package:prana_mobile/models/station.dart';

void main() {
  StationModel station() => StationModel(
    id: 'station-1',
    name: 'VINH',
    platform: 'linux',
    active: true,
    captureState: 'idle',
    desired: const DesiredState(
      running: false,
      targetLanguage: 'en',
      retryGeneration: 0,
      generation: 1,
    ),
    observedGeneration: 1,
    sessionId: 'session-1',
    sequence: 0,
    lastSeenAt: DateTime.now(),
  );

  TxController controller({bool running = true}) {
    final subject = TxController(
      stationId: 'station-1',
      repository: FakeTxRepository(
        processingDelay: Duration.zero,
        transmissionDelay: Duration.zero,
      ),
      queuePreviewDuration: Duration.zero,
    );
    subject.setStationAvailability(
      online: true,
      running: running,
      commandPending: false,
    );
    return subject;
  }

  Widget harness(TxController subject) => MaterialApp(
    theme: PranaTheme.light(),
    locale: const Locale('en'),
    supportedLocales: AppText.supportedLocales,
    localizationsDelegates: const [
      GlobalMaterialLocalizations.delegate,
      GlobalWidgetsLocalizations.delegate,
      GlobalCupertinoLocalizations.delegate,
    ],
    home: Scaffold(
      appBar: LiveHeader(
        station: station(),
        online: true,
        ux: const LiveUxState(),
        txController: subject,
        onToggle: () {},
        onSettings: () {},
      ),
      body: Column(
        children: [
          const Expanded(child: SizedBox()),
          TxLiveDock(
            controller: subject,
            stationState: 'IDLE',
            stationOnline: true,
            apiOnline: true,
            onReview: () {},
          ),
        ],
      ),
    ),
  );

  testWidgets('PTT stays below Live and changes RX badge to TX while held', (
    tester,
  ) async {
    final subject = controller();
    addTearDown(subject.dispose);
    await tester.pumpWidget(harness(subject));

    expect(find.text('RX IDLE'), findsOneWidget);
    expect(find.text('API READY'), findsOneWidget);
    expect(find.text('TX LANGUAGE'), findsOneWidget);
    final regionCenter =
        tester.getCenter(find.byKey(const ValueKey('tx-language-region'))).dx;
    final controlCenter =
        tester.getCenter(find.byKey(const ValueKey('tx-dock-language'))).dx;
    expect(controlCenter, closeTo(regionCenter, .1));
    final dockCenter =
        tester.getCenter(find.byKey(const ValueKey('tx-live-dock'))).dx;
    final pttCenter =
        tester.getCenter(find.byKey(const ValueKey('tx-center-control'))).dx;
    expect(pttCenter, closeTo(dockCenter, .1));
    final valueRight =
        tester.getTopRight(find.byKey(const ValueKey('tx-language-value'))).dx;
    final chevronLeft =
        tester.getTopLeft(find.byKey(const ValueKey('tx-language-chevron'))).dx;
    expect(chevronLeft - valueRight, closeTo(8, .1));

    await tester.tap(find.byKey(const ValueKey('tx-dock-language')));
    await tester.pumpAndSettle();
    expect(find.byType(PopupMenuItem<String>), findsNWidgets(5));
    expect(find.byIcon(Icons.check), findsOneWidget);
    await tester.tap(find.text('English'));
    await tester.pumpAndSettle();
    expect(subject.state.targetLanguage, 'en');

    final gesture = await tester.startGesture(
      tester.getCenter(find.byKey(const ValueKey('tx-ptt-button'))),
    );
    await tester.pump(const Duration(milliseconds: 200));

    expect(subject.state.phase, TxPhase.recording);
    expect(find.text('RX IDLE'), findsNothing);
    expect(find.text('TX'), findsWidgets);
    await tester.tap(find.byKey(const ValueKey('tx-dock-language')));
    await tester.pump();
    expect(find.byType(PopupMenuItem<String>), findsNothing);

    await gesture.up();
    await tester.pumpAndSettle();

    expect(subject.state.phase, TxPhase.reviewReady);
    expect(find.byKey(const ValueKey('tx-open-review')), findsOneWidget);
  });

  testWidgets('dock fits a 360dp screen at 1.3 text scale', (tester) async {
    tester.view.physicalSize = const Size(360, 800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final subject = controller();
    addTearDown(subject.dispose);

    await tester.pumpWidget(
      MediaQuery(
        data: const MediaQueryData(
          size: Size(360, 800),
          textScaler: TextScaler.linear(1.3),
        ),
        child: harness(subject),
      ),
    );

    expect(find.byKey(const ValueKey('tx-live-dock')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('PTT is disabled until Station is started', (tester) async {
    final subject = controller(running: false);
    addTearDown(subject.dispose);
    await tester.pumpWidget(harness(subject));

    expect(find.text('START FIRST'), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('tx-ptt-button')));
    await tester.pump();
    expect(subject.state.phase, TxPhase.idle);
  });
}
