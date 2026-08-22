import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/core/localization.dart';
import 'package:prana_mobile/core/theme.dart';
import 'package:prana_mobile/features/settings/station_settings_screen.dart';
import 'package:prana_mobile/models/station.dart';
import 'package:prana_mobile/providers.dart';

void main() {
  final now = DateTime(2026, 7, 27, 12);

  StationModel station({
    String captureMode = 'device',
    String audioDeviceId = 'device-id',
    int observedGeneration = 1,
    int desiredGeneration = 1,
    String storageFolder = 'Station_station-',
    bool secondSoundCard = false,
  }) => StationModel(
    id: 'station-1',
    name: 'Station',
    storageFolder: storageFolder,
    platform: 'windows',
    active: true,
    captureState: 'idle',
    desired: DesiredState(
      running: false,
      targetLanguage: 'vi',
      retryGeneration: 0,
      captureMode: captureMode,
      audioDeviceId: audioDeviceId,
      txAudioDeviceId: 'device-id',
      generation: desiredGeneration,
    ),
    observedGeneration: observedGeneration,
    sessionId: '',
    sequence: 0,
    lastSeenAt: now,
    capabilities: StationCapabilities(
      capabilityHash: 'hash',
      captureModes: const ['device', 'loopback'],
      audioDevices: [
        const StationAudioDevice(
          id: 'loopback-id',
          name: 'Speaker (Realtek Audio) [Loopback]',
          mode: 'loopback',
          inputChannels: 2,
          outputChannels: 0,
          sampleRate: 48000,
          hostApi: 'Windows WASAPI',
        ),
        // The USB card the radio is wired to: half-duplex, in and out.
        const StationAudioDevice(
          id: 'device-id',
          name: 'USB Audio Device: - (hw:3,0)',
          mode: 'device',
          inputChannels: 1,
          outputChannels: 2,
          sampleRate: 44100,
          hostApi: 'ALSA',
        ),
        if (secondSoundCard)
          const StationAudioDevice(
            id: 'second-output-id',
            name: 'USB Audio Device: - (hw:4,0)',
            mode: 'device',
            inputChannels: 1,
            outputChannels: 2,
            sampleRate: 44100,
            hostApi: 'ALSA',
          ),
      ],
      storagePath:
          r'D:\A very long Station storage folder\with several nested folders',
      updatedAt: now,
    ),
    activeCaptureMode: captureMode,
    activeAudioDeviceId: audioDeviceId,
  );

  Widget harness(StationModel value, {double textScale = 1}) => ProviderScope(
    overrides: [
      stationProvider.overrideWith((ref, stationId) => Stream.value(value)),
      stationClockProvider.overrideWith((ref) => Stream.value(now)),
    ],
    child: MaterialApp(
      theme: PranaTheme.light(),
      locale: const Locale('vi'),
      supportedLocales: AppText.supportedLocales,
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      builder:
          (context, child) => MediaQuery(
            data: MediaQuery.of(
              context,
            ).copyWith(textScaler: TextScaler.linear(textScale)),
            child: child!,
          ),
      home: const StationSettingsScreen(stationId: 'station-1'),
    ),
  );

  FilledButton saveButton(WidgetTester tester) => tester.widget<FilledButton>(
    find.widgetWithText(FilledButton, 'Lưu thay đổi'),
  );

  testWidgets('the station code moved out to Account and plan', (tester) async {
    await tester.pumpWidget(harness(station(storageFolder: 'VINH_0f90cd8e')));
    await tester.pumpAndSettle();

    expect(find.text('Mã trạm'), findsNothing);
    expect(find.text('VINH_0f90cd8e'), findsNothing);
    expect(find.byIcon(Icons.copy_outlined), findsNothing);
  });

  testWidgets('save is enabled only while capture settings are dirty', (
    tester,
  ) async {
    await tester.pumpWidget(harness(station()));
    await tester.pumpAndSettle();

    expect(find.text('Tự bắt đầu thu'), findsNothing);
    expect(saveButton(tester).onPressed, isNull);

    await tester.tap(find.text('LOOPBACK'));
    await tester.pump();
    expect(saveButton(tester).onPressed, isNotNull);

    await tester.tap(find.text('DEVICE'));
    await tester.pump();
    expect(saveButton(tester).onPressed, isNull);
  });

  testWidgets('one sound card asks nothing but still says where TX goes', (
    tester,
  ) async {
    await tester.pumpWidget(harness(station()));
    await tester.pumpAndSettle();

    // Half-duplex on a single card: no second question to answer.
    expect(find.text('Nguồn thu'), findsOneWidget);
    expect(find.text('Đầu ra TX'), findsNothing);
    expect(find.byKey(const ValueKey('tx-output-device')), findsNothing);
    // ...but the route is stated rather than silently assumed.
    expect(find.byKey(const ValueKey('tx-output-route')), findsOneWidget);
    expect(
      find.textContaining('Phát TX qua: USB Audio Device: - (hw:3,0)'),
      findsOneWidget,
    );
    // The Laptop-only wording is gone; a Station can be a Pi.
    expect(find.textContaining('Laptop'), findsNothing);
  });

  testWidgets('a second sound card brings the TX picker back', (tester) async {
    await tester.pumpWidget(harness(station(secondSoundCard: true)));
    await tester.pumpAndSettle();

    final txField = find.byKey(const ValueKey('tx-output-device'));
    expect(txField, findsOneWidget);
    expect(find.byKey(const ValueKey('tx-output-route')), findsNothing);
    expect(find.text('Thiết bị phát (TX)'), findsOneWidget);

    // One card holds the title, both dropdowns, and the rescan.
    final audioCard = find.ancestor(
      of: find.text('Nguồn thu'),
      matching: find.byType(Card),
    );
    expect(audioCard, findsOneWidget);
    expect(find.descendant(of: audioCard, matching: txField), findsOneWidget);
    final rescan = find.widgetWithText(OutlinedButton, 'Quét lại thiết bị');
    expect(find.descendant(of: audioCard, matching: rescan), findsOneWidget);

    // RX device, then TX device, then the rescan that refreshes both.
    final rxTop = tester.getTopLeft(find.text('Thiết bị âm thanh')).dy;
    final txTop = tester.getTopLeft(txField).dy;
    expect(txTop, greaterThan(rxTop));
    expect(tester.getTopLeft(rescan).dy, greaterThan(txTop));

    // TX still defaults to the card RX records on.
    expect(saveButton(tester).onPressed, isNull);
  });

  testWidgets('settings layout fits a narrow screen with scaled text', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(360, 720);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(harness(station(), textScale: 1.3));
    await tester.pumpAndSettle();

    expect(find.text('Nguồn thu'), findsOneWidget);
    expect(find.text('Thông tin Station'), findsOneWidget);
    expect(find.text('Lưu thay đổi'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('pending Station command disables the save action', (
    tester,
  ) async {
    await tester.pumpWidget(
      harness(station(observedGeneration: 1, desiredGeneration: 2)),
    );
    await tester.pump();

    expect(find.text('Đang áp dụng…'), findsOneWidget);
    expect(
      tester
          .widget<FilledButton>(
            find.widgetWithText(FilledButton, 'Đang áp dụng…'),
          )
          .onPressed,
      isNull,
    );
  });
}
