import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/app/app.dart';
import 'package:prana_mobile/app/di/auth_providers.dart';
import 'package:prana_mobile/app/di/radio_providers.dart';
import 'package:prana_mobile/app/di/telemetry_providers.dart';
import 'package:prana_mobile/app/di/station_providers.dart';
import 'package:prana_mobile/app/navigation/router.dart';
import 'package:prana_mobile/domain/radio/tx/tx_phase.dart';
import 'package:prana_mobile/domain/radio/tx/tx_draft.dart';
import 'package:prana_mobile/features/station/settings/station_settings_controller.dart';
import 'package:prana_mobile/features/station/history/history_screen.dart';
import 'package:prana_mobile/preview/demo_store.dart';
import 'package:prana_mobile/preview/demo_api.dart';
import 'package:prana_mobile/preview/demo_adapters.dart';
import 'package:prana_mobile/preview/preview_app.dart';
import 'package:prana_mobile/preview/preview_storage.dart';

Future<void> frames(WidgetTester tester, [int count = 6]) async {
  for (var i = 0; i < count; i++) {
    await tester.pump(const Duration(milliseconds: 100));
  }
}

ProviderContainer containerOf(WidgetTester tester) =>
    ProviderScope.containerOf(tester.element(find.byType(PranaMobileApp)));

void main() {
  testWidgets(
    'History detail filters persist and manual playback stops on leaving',
    (tester) async {
      tester.view.physicalSize = const Size(1024, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final store = DemoStore(ticking: false);
      await tester.pumpWidget(PreviewSession(onReset: () {}, store: store));
      await frames(tester);
      final container = containerOf(tester);
      final router = container.read(routerProvider);
      router.go('/stations/demo-online/history');
      await frames(tester);
      await tester.tap(find.byIcon(Icons.calendar_today_outlined).first);
      await frames(tester);
      await tester.enterText(find.byType(TextField).first, 'harbor');
      await frames(tester);
      expect(find.textContaining('Harbor control'), findsWidgets);
      router.replace('/stations/demo-online/control');
      await frames(tester);
      router.replace('/stations/demo-online/history');
      await frames(tester);
      expect(
        tester.widget<TextField>(find.byType(TextField).first).controller!.text,
        'harbor',
      );
      tester.state<HistoryScreenState>(find.byType(HistoryScreen)).backToDays();
      await frames(tester);
      await tester.tap(find.text('TX'));
      await frames(tester);
      await tester.tap(find.byIcon(Icons.calendar_today_outlined).first);
      await frames(tester);
      await tester.tap(find.byIcon(Icons.volume_up_outlined).first);
      await frames(tester, 1);
      expect(find.byIcon(Icons.stop_circle_outlined), findsOneWidget);
      router.replace('/stations/demo-online/control');
      await frames(tester, 2);
      router.replace('/stations/demo-online/history');
      await frames(tester, 2);
      expect(find.byIcon(Icons.stop_circle_outlined), findsNothing);
      expect(store.commandCount, 0);
      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pump();
      expect(store.projectionSubscriptions, 0);
      expect(store.resultsSubscriptions, 0);
    },
  );
  test(
    'one store keeps desired, RX and history consistent, and disposes streams',
    () async {
      var now = DateTime(2026, 9, 12, 12);
      final store = DemoStore(clock: () => now, ticking: false);
      final api = DemoApi(store);
      final repository = DemoStationRepository(store);
      final seen = <bool>[];
      final sub = repository
          .watchStation('demo', 'demo-online')
          .listen((station) => seen.add(station!.desired.running));
      await Future<void>.delayed(Duration.zero);
      expect(store.stationModels.first.isOnlineAt(now), isTrue);
      expect(store.stationModels.last.isOnlineAt(now), isFalse);
      expect(store.commandCount, 0);
      await api.setDesiredState('demo-online', running: true);
      for (var i = 0; i < 5; i++) {
        now = now.add(const Duration(seconds: 1));
        store.tick();
      }
      final live = await api.stationLiveResults(
        'demo-online',
        timezoneOffsetMinutes: 420,
      );
      final history = await api.stationHistoryDayResults(
        'demo-online',
        '2026-09-12',
        timezoneOffsetMinutes: 420,
      );
      expect(live.map((r) => r.requestId), history.map((r) => r.requestId));
      expect(live.length, 4);
      await api.setDesiredState('demo-online', running: false);
      for (var i = 0; i < 10; i++) {
        store.tick();
      }
      expect(store.results['demo-online']!.length, 10);
      await Future<void>.delayed(Duration.zero);
      expect(seen, containsAll([false, true]));
      await sub.cancel();
      expect(store.projectionSubscriptions, 0);
      store.dispose();
    },
  );

  test('Settings refresh/save and Account updates are session only', () async {
    final store = DemoStore(ticking: false);
    final repo = DemoStationRepository(store);
    final settings = StationSettingsController(
      repo,
      'demo-online',
      () => store.stationModels.first,
    );
    expect(
      await settings.save(
        audioDeviceId: 'demo-usb-alt',
        txAudioDeviceId: 'demo-usb-alt',
      ),
      isTrue,
    );
    expect(store.stationModels.first.activeAudioDeviceId, 'demo-usb-alt');
    expect(await settings.refresh(store.stationModels.first), isNotNull);
    final api = DemoApi(store);
    await api.updateRegion(countryCode: 'SG');
    await api.selectPlan('demo-basic');
    expect((await api.account())['country_code'], 'SG');
    expect((await api.account())['plan_id'], 'demo-basic');
    final next = DemoStore(ticking: false);
    expect(next.account['country_code'], 'VN');
    expect(next.stationModels.first.activeAudioDeviceId, 'demo-usb');
    settings.dispose();
    store.dispose();
    next.dispose();
  });

  test(
    'playback stop completes pending play; storage isolates visual preferences',
    () async {
      final player = DemoPlayback();
      final playing = player.play('demo', 'job');
      expect(player.playing, isTrue);
      await player.stop();
      await playing;
      expect(player.playing, isFalse);
      await player.dispose();
      final storage = PreviewStorage();
      await storage.write(key: 'dark_mode', value: 'true');
      await storage.write(key: 'app_locale', value: 'vi');
      await storage.write(key: 'user_country', value: 'SG');
      final next = PreviewStorage();
      expect(await next.read(key: 'dark_mode'), 'true');
      expect(await next.read(key: 'app_locale'), 'vi');
      expect(await next.read(key: 'user_country'), isNull);
      await next.write(key: 'dark_mode', value: null);
      await next.write(key: 'app_locale', value: null);
    },
  );

  testWidgets(
    'real routes keep session, telemetry and draft; no Firebase access',
    (tester) async {
      tester.view.physicalSize = const Size(1024, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      var now = DateTime.now();
      final store = DemoStore(clock: () => now, ticking: false);
      await tester.pumpWidget(PreviewSession(onReset: () {}, store: store));
      await frames(tester);
      final container = containerOf(tester);
      final router = container.read(routerProvider);
      expect(find.text('VINH Station'), findsOneWidget);
      expect(find.text('Harbor Station'), findsOneWidget);
      expect(() => container.read(authProvider), throwsA(isA<Exception>()));
      expect(
        () => container.read(firestoreProvider),
        throwsA(isA<Exception>()),
      );
      router.go('/stations/demo-online/control');
      await frames(tester);
      final session = container.read(stationSessionProvider('demo-online'));
      final telemetry = container.read(
        stationTelemetryControllerProvider('demo-online'),
      );
      final subscriptions = store.projectionSubscriptions;
      for (final page in ['live', 'history', 'settings', 'control']) {
        router.replace('/stations/demo-online/$page');
        await frames(tester);
        expect(
          container.read(stationSessionProvider('demo-online')),
          same(session),
        );
        expect(
          container.read(stationTelemetryControllerProvider('demo-online')),
          same(telemetry),
        );
        expect(store.projectionSubscriptions, subscriptions);
        expect(store.commandCount, 0);
        expect(tester.takeException(), isNull);
      }
      await container.read(appThemeModeProvider).setDarkMode(true);
      await container.read(appLocaleProvider).setLocale('vi');
      await frames(tester);
      expect(container.read(routerProvider), same(router));
      expect(
        container.read(stationSessionProvider('demo-online')),
        same(session),
      );
      await container
          .read(apiProvider)
          .setDesiredState('demo-online', running: true);
      await frames(tester);
      router.replace('/stations/demo-online/live');
      await frames(tester);
      session.tx.startRecording();
      await frames(tester, 2);
      expect(session.tx.state.phase, TxPhase.recording);
      await tester.tap(find.text('Control').first);
      await frames(tester, 12);
      expect(session.tx.state.phase, TxPhase.reviewReady);
      expect(find.byType(BottomSheet), findsNothing);
      final draft = session.tx.state.draft!;
      expect(store.drafts[draft.id]!.status, 'review_ready');
      router.replace('/stations/demo-online/live');
      await frames(tester);
      await tester.enterText(find.byType(TextField).last, 'Edited preview');
      router.pop();
      await frames(tester);
      router.replace('/stations/demo-online/settings');
      await frames(tester);
      expect(session.tx.state.draft!.id, draft.id);
      final confirmed = session.tx.confirmTransmission('Edited preview');
      await frames(tester, 2);
      now = now.add(const Duration(seconds: 3));
      store.tick();
      await frames(tester, 12);
      expect(session.tx.state.phase, TxPhase.transmitting);
      now = now.add(const Duration(seconds: 4));
      store.tick();
      await frames(tester, 12);
      await confirmed;
      expect(store.drafts[draft.id]!.status, 'completed');
      expect(store.commandCount, 1);
      router.go('/account');
      await frames(tester);
      expect(tester.takeException(), isNull);
      await container.read(authenticationServiceProvider).signOut();
      await frames(tester);
      expect(find.text('Phiên demo đã kết thúc'), findsOneWidget);
      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pump();
      expect(store.disposed, isTrue);
      expect(store.projectionSubscriptions, 0);
    },
  );

  testWidgets('reset creates a clean demo and preserves locale/theme', (
    tester,
  ) async {
    await tester.pumpWidget(const PreviewApp());
    await frames(tester);
    final first = containerOf(tester);
    for (final key in ['preview-text-scale', 'preview-reset']) {
      expect(
        tester.getSize(find.byKey(ValueKey(key))).height,
        greaterThanOrEqualTo(48),
      );
    }
    await first.read(appThemeModeProvider).setDarkMode(true);
    await first.read(appLocaleProvider).setLocale('vi');
    await first.read(apiProvider).removeStation('demo-offline');
    await frames(tester);
    expect(find.text('Harbor Station'), findsNothing);
    await tester.tap(find.byKey(const ValueKey('preview-reset')));
    await frames(tester);
    final next = containerOf(tester);
    expect(next, isNot(same(first)));
    expect(find.text('Harbor Station'), findsOneWidget);
    expect(next.read(appThemeModeProvider).darkMode, isTrue);
    expect(next.read(appLocaleProvider).locale!.languageCode, 'vi');
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump();
  });

  testWidgets('late TX process after reset cannot write into new session', (
    tester,
  ) async {
    final old = DemoStore(ticking: false);
    final repo = DemoTxRepository(old);
    final process = repo.processRecording(
      const TxRecordingInput(
        stationId: 'demo-online',
        duration: Duration(seconds: 2),
        targetLanguage: 'en',
        requestId: 'late',
      ),
    );
    final assertion = expectLater(process, throwsStateError);
    old.dispose();
    final next = DemoStore(ticking: false);
    await tester.pump(const Duration(seconds: 1));
    await assertion;
    expect(next.activeDrafts, isEmpty);
    expect(next.drafts.containsKey('late'), isFalse);
    next.dispose();
  });
}
