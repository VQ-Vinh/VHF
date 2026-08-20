import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/core/localization.dart';
import 'package:prana_mobile/core/theme.dart';
import 'package:prana_mobile/features/live/live_screen.dart';
import 'package:prana_mobile/features/tx/application/fake_tx_repository.dart';
import 'package:prana_mobile/features/tx/application/tx_controller.dart';
import 'package:prana_mobile/features/tx/domain/tx_phase.dart';
import 'package:prana_mobile/features/tx/presentation/widgets/tx_live_dock.dart';
import 'package:prana_mobile/features/tx/presentation/widgets/tx_ptt_button.dart';

void _ignore(String _) {}

void main() {
  Widget wrap(Widget child) => MaterialApp(
    theme: PranaTheme.light(),
    locale: const Locale('en'),
    supportedLocales: AppText.supportedLocales,
    localizationsDelegates: const [
      GlobalMaterialLocalizations.delegate,
      GlobalWidgetsLocalizations.delegate,
      GlobalCupertinoLocalizations.delegate,
    ],
    home: Scaffold(body: child),
  );

  TxController controller() {
    final subject = TxController(
      stationId: 'station-1',
      repository: FakeTxRepository(
        processingDelay: Duration.zero,
        transmissionDelay: Duration.zero,
      ),
      queuePreviewDuration: Duration.zero,
      maximumDuration: const Duration(seconds: 60),
    );
    subject.setStationAvailability(
      online: true,
      running: true,
      commandPending: false,
    );
    return subject;
  }

  Finder pttShell() => find.descendant(
    of: find.byKey(const ValueKey('tx-ptt-button')),
    matching: find.byType(AnimatedContainer),
  );

  testWidgets('PTT is a circle carrying only the mic and its label', (
    tester,
  ) async {
    await tester.pumpWidget(
      wrap(
        Center(
          child: TxPttButton(
            diameter: 160,
            enabled: true,
            recording: false,
            onHoldStart: () {},
            onHoldEnd: () {},
          ),
        ),
      ),
    );

    final size = tester.getSize(pttShell());
    expect(size.width, 160);
    expect(size.height, size.width);

    final decoration =
        tester.widget<AnimatedContainer>(pttShell()).decoration as BoxDecoration;
    expect(decoration.shape, BoxShape.circle);

    expect(find.text('HOLD TO TALK'), findsOneWidget);
    expect(find.byIcon(Icons.mic_none), findsOneWidget);
    expect(find.textContaining('MAX'), findsNothing);

    // Mic sits at the centre with the label directly beneath it.
    final iconCenter = tester.getCenter(find.byIcon(Icons.mic_none));
    final labelCenter = tester.getCenter(find.text('HOLD TO TALK'));
    final shellCenter = tester.getCenter(pttShell());
    expect(iconCenter.dx, closeTo(shellCenter.dx, .1));
    expect(labelCenter.dx, closeTo(shellCenter.dx, .1));
    expect(labelCenter.dy, greaterThan(iconCenter.dy));
    expect(tester.takeException(), isNull);
  });

  testWidgets('talk pad shrinks the circle to fit a short 360dp screen', (
    tester,
  ) async {
    final subject = controller();
    addTearDown(subject.dispose);
    tester.view.physicalSize = const Size(360, 640);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      wrap(
        Column(
          children: [
            const Expanded(flex: 4, child: SizedBox()),
            Expanded(
              flex: 5,
              child: TxTalkPad(
                controller: subject,
                onReview: () {},
                onConnectionRetry: () {},
              ),
            ),
          ],
        ),
      ),
    );

    final padHeight = tester.getSize(
      find.byKey(const ValueKey('tx-talk-pad')),
    ).height;
    final buttonSize = tester.getSize(pttShell());
    expect(buttonSize.width, buttonSize.height);
    expect(buttonSize.height, lessThanOrEqualTo(padHeight));
    expect(buttonSize.width, greaterThanOrEqualTo(112));
    expect(buttonSize.width, lessThanOrEqualTo(200));
    expect(tester.takeException(), isNull);
  });

  testWidgets('talk pad does not overflow a landscape phone', (tester) async {
    final subject = controller();
    addTearDown(subject.dispose);
    // Landscape leaves this row shorter than the smallest circle (112).
    await tester.pumpWidget(
      wrap(
        Align(
          alignment: Alignment.topCenter,
          child: SizedBox(
            height: 64,
            width: 800,
            child: TxTalkPad(
              controller: subject,
              onReview: () {},
              onConnectionRetry: () {},
            ),
          ),
        ),
      ),
    );

    // The block is scaled down rather than painted past the pad's bottom edge.
    expect(find.byKey(const ValueKey('tx-ptt-button')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('TX language field matches the RX field frame', (
    tester,
  ) async {
    final subject = controller();
    addTearDown(subject.dispose);

    await tester.pumpWidget(
      wrap(
        Column(
          children: [
            const LanguageStrip(
              detectedLanguage: 'vi',
              targetLanguage: 'en',
              enabled: true,
              onChanged: _ignore,
            ),
            const Spacer(),
            TxLiveDock(
              controller: subject,
              stationState: 'IDLE',
              stationOnline: true,
              apiOnline: true,
            ),
          ],
        ),
      ),
    );

    // Both keys cover label + field, so equal heights mean equal typography
    // and an equal 40px box underneath.
    final stripRegion = tester.getSize(
      find.byKey(const ValueKey('input-language-field')),
    );
    final txRegion = tester.getSize(
      find.byKey(const ValueKey('tx-language-region')),
    );
    expect(txRegion.height, stripRegion.height);
    expect(
      tester.getSize(find.byKey(const ValueKey('tx-dock-language'))).height,
      40,
    );

    final decoration =
        tester
                .widget<Container>(
                  find.descendant(
                    of: find.byKey(const ValueKey('tx-dock-language')),
                    matching: find.byType(Container),
                  ),
                )
                .decoration
            as BoxDecoration;
    expect(decoration.color, PranaTheme.surface);
    expect(decoration.borderRadius, BorderRadius.circular(11));
    expect(decoration.border, Border.all(color: const Color(0xFFB9CDD2)));
    expect(tester.takeException(), isNull);
  });

  testWidgets('language labels read as directions in both locales', (
    tester,
  ) async {
    // AppText.of falls back to the raw key when a lookup misses, so a key
    // renamed in only one map would ship its own name to the user.
    for (final (locale, heard, translateTo, transmitIn) in const [
      (Locale('en'), 'HEARD', 'TRANSLATE TO', 'TRANSMIT IN'),
      (Locale('vi'), 'NGHE ĐƯỢC', 'DỊCH SANG', 'PHÁT BẰNG'),
    ]) {
      final subject = controller();
      addTearDown(subject.dispose);

      await tester.pumpWidget(
        MaterialApp(
          theme: PranaTheme.light(),
          locale: locale,
          supportedLocales: AppText.supportedLocales,
          localizationsDelegates: const [
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          home: Scaffold(
            body: Column(
              children: [
                const LanguageStrip(
                  detectedLanguage: 'vi',
                  targetLanguage: 'en',
                  enabled: true,
                  onChanged: _ignore,
                ),
                const Spacer(),
                TxLiveDock(
                  controller: subject,
                  stationState: 'IDLE',
                  stationOnline: true,
                  apiOnline: true,
                ),
              ],
            ),
          ),
        ),
      );

      expect(find.text(heard), findsOneWidget, reason: '$locale heard');
      expect(find.text(translateTo), findsOneWidget, reason: '$locale target');
      expect(find.text(transmitIn), findsOneWidget, reason: '$locale transmit');
      for (final key in const [
        'rx_heard',
        'rx_translate_to',
        'tx_transmit_in',
      ]) {
        expect(find.textContaining(key), findsNothing, reason: '$locale $key');
      }
      expect(tester.takeException(), isNull);
    }
  });

  testWidgets('a completed transmission shows no button to acknowledge', (
    tester,
  ) async {
    // A long linger keeps the indicator on screen; the timing itself is
    // covered by tx_controller_test.
    final subject = TxController(
      stationId: 'station-1',
      repository: FakeTxRepository(
        processingDelay: Duration.zero,
        transmissionDelay: Duration.zero,
      ),
      queuePreviewDuration: Duration.zero,
      completedLingerDuration: const Duration(seconds: 10),
    );
    subject.setStationAvailability(
      online: true,
      running: true,
      commandPending: false,
    );
    addTearDown(subject.dispose);
    // Real timers: the TX flow polls, which the widget clock never advances.
    await tester.runAsync(() async {
      subject.startRecording();
      await subject.stopRecording();
      await subject.confirmTransmission('Cấp cứu.');
    });
    expect(subject.state.phase, TxPhase.completed);

    await tester.pumpWidget(
      wrap(
        TxTalkPad(
          controller: subject,
          onReview: () {},
          onConnectionRetry: () {},
        ),
      ),
    );

    final indicator = find.byKey(const ValueKey('tx-done-indicator'));
    expect(indicator, findsOneWidget);
    expect(find.text('DONE'), findsOneWidget);
    // Nothing to tap: the controller clears this on its own.
    expect(
      find.descendant(of: indicator, matching: find.byType(InkWell)),
      findsNothing,
    );
    // Same circle as the PTT, not the old small rectangle.
    final shell = tester.widget<Container>(
      find.descendant(of: indicator, matching: find.byType(Container)).first,
    );
    expect((shell.decoration as BoxDecoration).shape, BoxShape.circle);
    final size = tester.getSize(
      find.descendant(of: indicator, matching: find.byType(Container)).first,
    );
    expect(size.width, size.height);
    expect(tester.takeException(), isNull);
  });

  test('live feed renders only the newest translation', () {
    final source =
        File('lib/features/live/live_screen.dart').readAsStringSync();

    // Newest last: results are sorted chronologically ascending upstream.
    expect(source, contains('final newest = items.last;'));
    expect(source, contains('result: newest'));
    expect(source, contains('items.last.language'));
    // The scrolling feed and its auto-stick-to-bottom machinery are gone.
    expect(source, isNot(contains('ListView.separated')));
    expect(source, isNot(contains('_scrollToNewest')));
    expect(source, isNot(contains('_visibleResultSignature')));
    // History stays the way back to older translations.
    expect(source, contains('onPressed: onHistory'));
  });
}
