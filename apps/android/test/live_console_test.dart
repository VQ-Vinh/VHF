import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/app/di/radio_providers.dart';
import 'package:prana_mobile/core/theme.dart';
import 'package:prana_mobile/domain/radio/source_audio_engine.dart';
import 'package:prana_mobile/domain/radio/speech_engine.dart';
import 'package:prana_mobile/domain/radio/tx/tx_phase.dart';
import 'package:prana_mobile/domain/radio/vhf_channel.dart';
import 'package:prana_mobile/domain/station/station.dart';
import 'package:prana_mobile/features/station/radio/presentation/live_screen.dart';
import 'package:prana_mobile/features/station/radio/presentation/widgets/tx/ptt_instrument.dart';
import 'package:prana_mobile/features/station/radio/presentation/widgets/tx/tx_live_dock.dart';
import 'package:prana_mobile/l10n/app_localizations.dart';
import 'package:prana_mobile/runtime/vhf/live_controller.dart';
import 'package:prana_mobile/runtime/vhf/translation_speech.dart';
import 'package:prana_mobile/runtime/vhf/tx_controller.dart';
import 'support/fake_tx_repository.dart';

class _Speech implements SpeechEngine {
  @override
  Future<String?> resolveLocale(String locale) async => locale;
  @override
  Future<void> speak(String text, String locale) async {}
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

void main() {
  // Built once. A fresh ThemeData on every pump makes MaterialApp's
  // AnimatedTheme lerp for 200ms, which is the harness moving, not the console.
  final lightTheme = PranaTheme.light();
  final darkTheme = PranaTheme.dark();

  StationModel station({String capture = 'listening', bool running = true}) =>
      StationModel(
        id: 'station-1',
        name: 'VINH',
        platform: 'linux',
        active: true,
        captureState: capture,
        desired: DesiredState(
          running: running,
          targetLanguage: 'en',
          retryGeneration: 0,
          generation: 1,
        ),
        observedGeneration: 1,
        sessionId: 'session-1',
        sequence: 0,
        lastSeenAt: DateTime.now(),
      );

  TxController controller() {
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
      running: true,
      commandPending: false,
    );
    return subject;
  }

  /// The console as LiveScreen stacks it, without the Station providers.
  Widget console({
    required TxController tx,
    StationModel? model,
    PttChannelState channelState = PttChannelState.listening,
    VhfChannel channel = const VhfChannel(16, simulated: true),
    VoidCallback? onReview,
    bool dark = false,
    Locale locale = const Locale('en'),
    double scale = 1,
    bool reduceMotion = false,
  }) => ProviderScope(
    overrides: [
      translationSpeechProvider.overrideWith(
        (ref) => TranslationSpeechController(_Speech(), _Audio()),
      ),
    ],
    child: MaterialApp(
      theme: dark ? darkTheme : lightTheme,
      locale: locale,
      supportedLocales: AppLocalizations.supportedLocales,
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      builder:
          (context, child) => MediaQuery(
            data: MediaQuery.of(context).copyWith(
              textScaler: TextScaler.linear(scale),
              disableAnimations: reduceMotion,
            ),
            child: child!,
          ),
      home: Scaffold(
        body: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              LiveHeader(
                station: model ?? station(),
                online: true,
                ux: const LiveUxState(),
                onToggle: () {},
                txController: tx,
                channel: channel,
                embedded: true,
              ),
              LanguageStrip(
                detectedLanguage: 'vi',
                targetLanguage: 'en',
                enabled: true,
                onChanged: (_) {},
              ),
              LiveFeedHeader(onHistory: () {}),
              TxTalkPad(
                controller: tx,
                onReview: onReview ?? () {},
                onConnectionRetry: () {},
                channelState: channelState,
              ),
              TxLiveDock(
                controller: tx,
                stationOnline: true,
                apiOnline: true,
                now: DateTime.utc(2026, 9, 11, 4, 48),
                onReview: onReview,
              ),
            ],
          ),
        ),
      ),
    ),
  );

  testWidgets('the console fits every width, locale, text scale and theme', (
    tester,
  ) async {
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    for (final size in const [
      Size(320, 800),
      Size(375, 812),
      Size(390, 844),
      Size(400, 800),
      Size(430, 932),
      Size(768, 1024),
      Size(1024, 768),
      Size(800, 320),
    ]) {
      for (final locale in const [Locale('vi'), Locale('en')]) {
        for (final scale in const [1.0, 1.5, 2.0]) {
          for (final dark in const [false, true]) {
            final reason = '$size/${locale.languageCode}/$scale/dark=$dark';
            tester.view.physicalSize = size;
            final tx = controller();
            await tester.pumpWidget(
              console(tx: tx, dark: dark, locale: locale, scale: scale),
            );
            await tester.pump();
            expect(tester.takeException(), isNull, reason: reason);
            for (final key in const [
              'live-toggle-button',
              'live-channel',
              'input-language-field',
              'output-language-field',
              'tx-dock-language',
              'tx-send-cell',
              'tx-status-clock',
            ]) {
              final rect = tester.getRect(find.byKey(ValueKey(key)));
              expect(
                rect.left,
                greaterThanOrEqualTo(0),
                reason: '$reason $key',
              );
              expect(
                rect.right,
                lessThanOrEqualTo(size.width),
                reason: '$reason $key',
              );
            }
            await tester.pumpWidget(const SizedBox.shrink());
            tx.dispose();
          }
        }
      }
    }
  });

  testWidgets('the capture key breaks between words, never inside one', (
    tester,
  ) async {
    // Wide enough that the capture cell stays a key at every scale, which is
    // the narrow, two-line layout this is about.
    tester.view.physicalSize = const Size(1024, 768);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    for (final locale in const [Locale('en'), Locale('vi')]) {
      for (final scale in const [1.0, 1.5, 2.0]) {
        for (final running in const [false, true]) {
          final tx = controller();
          await tester.pumpWidget(
            console(
              tx: tx,
              model: station(
                capture: running ? 'listening' : 'idle',
                running: running,
              ),
              locale: locale,
              scale: scale,
              reduceMotion: true,
            ),
          );
          final finder = find.byKey(const ValueKey('live-toggle-label'));
          final words = tester.widget<Text>(finder).data!.split(' ').length;
          final lineHeight = 11 * 1.25 * scale;
          final lines = (tester.getSize(finder).height / lineHeight).round();
          expect(
            lines,
            lessThanOrEqualTo(words),
            reason: '${locale.languageCode}/$scale/running=$running',
          );
          await tester.pumpWidget(const SizedBox.shrink());
          tx.dispose();
        }
      }
    }
  });

  testWidgets('the channel shows the number, and discloses the simulation', (
    tester,
  ) async {
    final tx = controller();
    addTearDown(tx.dispose);
    final semantics = tester.ensureSemantics();

    await tester.pumpWidget(console(tx: tx));
    expect(find.text('16'), findsOneWidget);
    // The cell carries the number alone; the disclosure rides the semantics
    // label, where it costs no space on a crowded hero row.
    expect(find.text('SIM'), findsNothing);
    expect(
      tester.getSemantics(find.byKey(const ValueKey('live-channel'))).label,
      contains('SIM'),
    );

    await tester.pumpWidget(console(tx: tx, locale: const Locale('vi')));
    expect(
      tester.getSemantics(find.byKey(const ValueKey('live-channel'))).label,
      contains('MÔ PHỎNG'),
    );

    // A channel a real source reports says nothing about simulation.
    await tester.pumpWidget(
      console(tx: tx, channel: const VhfChannel(72, simulated: false)),
    );
    expect(find.text('72'), findsOneWidget);
    expect(
      tester.getSemantics(find.byKey(const ValueKey('live-channel'))).label,
      isNot(contains('SIM')),
    );
    semantics.dispose();
  });

  testWidgets('the heard language reads as a name, between two rules', (
    tester,
  ) async {
    final tx = controller();
    addTearDown(tx.dispose);
    await tester.pumpWidget(console(tx: tx));

    // The name only: the two-letter code said the same thing twice. Scoped to
    // the field, because the TX dock names a language of its own.
    expect(
      find.descendant(
        of: find.byKey(const ValueKey('input-language-field')),
        matching: find.text('Tiếng Việt'),
      ),
      findsOneWidget,
    );
    expect(find.text('VI'), findsNothing);

    // The arrow sits in its own bay between the two fields: rule, arrow, rule.
    final heard = tester.getRect(
      find.byKey(const ValueKey('input-language-field')),
    );
    final target = tester.getRect(
      find.byKey(const ValueKey('output-language-field')),
    );
    final arrow = tester.getRect(find.byIcon(Icons.arrow_forward));
    final rules =
        tester.widgetList<VerticalDivider>(find.byType(VerticalDivider)).length;
    expect(rules, greaterThanOrEqualTo(2));
    expect(arrow.left, greaterThan(heard.right));
    expect(arrow.right, lessThan(target.left));
    expect(
      arrow.center.dx - heard.right,
      closeTo(target.left - arrow.center.dx, 1),
      reason: 'centred between the fields',
    );
  });

  testWidgets('speech on the channel reads as RX RECEIVING', (tester) async {
    final tx = controller();
    addTearDown(tx.dispose);
    await tester.pumpWidget(
      console(
        tx: tx,
        model: station(capture: 'recording'),
        channelState: PttChannelState.receiving,
      ),
    );
    expect(find.text('RX RECEIVING'), findsOneWidget);
    expect(find.text('RX RECORDING'), findsNothing);
  });

  testWidgets('the TX cell sends only once a draft is ready for review', (
    tester,
  ) async {
    final tx = controller();
    addTearDown(tx.dispose);
    var reviews = 0;
    InkWell send() =>
        tester.widget<InkWell>(find.byKey(const ValueKey('tx-send-cell')));

    await tester.pumpWidget(
      // Capture stopped, so nothing on screen loops and pumpAndSettle can
      // settle; a listening Station would keep the RX dot blinking.
      console(
        tx: tx,
        model: station(capture: 'idle', running: false),
        channelState: PttChannelState.idle,
        onReview: () => reviews++,
      ),
    );
    expect(send().onTap, isNull, reason: 'nothing to send yet');

    final gesture = await tester.startGesture(
      tester.getCenter(find.byKey(const ValueKey('tx-ptt-button'))),
    );
    await tester.pump(const Duration(milliseconds: 200));
    expect(tx.state.phase, TxPhase.recording);
    expect(send().onTap, isNull, reason: 'recording is not sending');
    await gesture.up();
    await tester.pumpAndSettle();

    expect(tx.state.phase, TxPhase.reviewReady);
    expect(send().onTap, isNotNull);
    await tester.tap(find.byKey(const ValueKey('tx-send-cell')));
    expect(reviews, 1);
  });

  testWidgets('nothing loops unless something is happening', (tester) async {
    final tx = controller();
    addTearDown(tx.dispose);

    // Capture stopped: no blinking dot, no sweep, a flat waveform.
    await tester.pumpWidget(
      console(
        tx: tx,
        model: station(capture: 'idle', running: false),
        channelState: PttChannelState.idle,
      ),
    );
    await tester.pump();
    expect(tester.binding.transientCallbackCount, 0, reason: 'idle');
    expect(tester.binding.hasScheduledFrame, isFalse, reason: 'idle');

    // Listening: the instrument sweeps and the dot blinks.
    await tester.pumpWidget(console(tx: tx));
    await tester.pump();
    expect(tester.binding.hasScheduledFrame, isTrue, reason: 'listening');
    // Let finite transitions finish before measuring: going from stopped to
    // running recolours the capture key, and Material crossfades that over
    // 200ms. That is a transition that ends, not a loop.
    await tester.pump(const Duration(milliseconds: 300));

    // Same state under reduced motion: still, and still readable.
    // One more frame than idle: stopping a running loop resets it to rest,
    // and drawing that rest is the last frame it asks for.
    await tester.pumpWidget(console(tx: tx, reduceMotion: true));
    await tester.pump();
    await tester.pump();
    expect(tester.binding.transientCallbackCount, 0, reason: 'reduced');
    expect(tester.binding.hasScheduledFrame, isFalse, reason: 'reduced');
    expect(find.text('RX LISTENING'), findsOneWidget);
    await tester.pumpWidget(const SizedBox.shrink());
  });
}
