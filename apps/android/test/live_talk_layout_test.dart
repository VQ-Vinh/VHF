import 'package:prana_mobile/l10n/app_localizations.dart';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:prana_mobile/features/station/radio/presentation/widgets/console_palette.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/core/theme.dart';
import 'package:prana_mobile/features/station/radio/presentation/live_screen.dart';
import 'support/fake_tx_repository.dart';
import 'package:prana_mobile/runtime/vhf/tx_controller.dart';
import 'package:prana_mobile/domain/radio/tx/tx_phase.dart';
import 'package:prana_mobile/features/station/radio/presentation/widgets/tx/tx_live_dock.dart';
import 'package:prana_mobile/features/station/radio/presentation/widgets/tx/tx_ptt_button.dart';

void _ignore(String _) {}

void main() {
  Widget wrap(Widget child) => MaterialApp(
    theme: PranaTheme.light(),
    locale: const Locale('en'),
    supportedLocales: AppLocalizations.supportedLocales,
    localizationsDelegates: const [
      AppLocalizations.delegate,
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

  testWidgets('resizing a held PTT keeps the pointer and releases once', (
    tester,
  ) async {
    var starts = 0;
    var stops = 0;
    Widget button(double diameter) => wrap(
      Center(
        child: TxPttButton(
          diameter: diameter,
          enabled: true,
          recording: false,
          onHoldStart: () => starts++,
          onHoldEnd: () => stops++,
        ),
      ),
    );
    await tester.pumpWidget(button(160));
    final gesture = await tester.startGesture(tester.getCenter(pttShell()));
    expect(starts, 1);
    await tester.pumpWidget(button(240));
    await tester.pump(const Duration(milliseconds: 80));
    expect(starts, 1);
    expect(stops, 0);
    expect(tester.takeException(), isNull);
    await gesture.up();
    expect(stops, 1);
  });

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
        tester.widget<AnimatedContainer>(pttShell()).decoration
            as BoxDecoration;
    expect(decoration.shape, BoxShape.circle);

    expect(find.text('HOLD TO TALK'), findsOneWidget);
    // The label reads TX · HOLD TO TALK, on two lines.
    expect(find.byKey(const ValueKey('tx-ptt-mode')), findsOneWidget);
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

  testWidgets('talk pad keeps a readable circle on a short 360dp screen', (
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

    final padHeight =
        tester.getSize(find.byKey(const ValueKey('tx-talk-pad'))).height;
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

  testWidgets('TX language field matches the RX field frame', (tester) async {
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
              stationOnline: true,
              apiOnline: true,
            ),
          ],
        ),
      ),
    );

    // Both fields grow with their labels and retain an accessible touch area.
    final stripRegion = tester.getSize(
      find.byKey(const ValueKey('input-language-field')),
    );
    final txRegion = tester.getSize(
      find.byKey(const ValueKey('tx-language-region')),
    );
    expect(txRegion.height, stripRegion.height);
    expect(
      tester.getSize(find.byKey(const ValueKey('tx-dock-language'))).height,
      greaterThanOrEqualTo(48),
    );

    // One frame for all three language fields: the console field, which has
    // no box and no radius. The rounded 11dp form card is gone by design.
    expect(
      tester.widget(find.byKey(const ValueKey('tx-language-region'))),
      isA<ConsoleField>(),
    );
    expect(
      tester.widget(find.byKey(const ValueKey('input-language-field'))),
      isA<ConsoleField>(),
    );
    expect(
      tester.widget(find.byKey(const ValueKey('output-language-field'))),
      isA<ConsoleField>(),
    );
    for (final region in const ['tx-language-region', 'input-language-field']) {
      final rounded = tester
          .widgetList<Container>(
            find.descendant(
              of: find.byKey(ValueKey(region)),
              matching: find.byType(Container),
            ),
          )
          .where(
            (box) =>
                box.decoration is BoxDecoration &&
                (box.decoration! as BoxDecoration).borderRadius != null,
          );
      expect(rounded, isEmpty, reason: region);
    }
    expect(tester.takeException(), isNull);
  });

  testWidgets('language labels read as directions in both locales', (
    tester,
  ) async {
    // Verify the generated translations preserve the radio direction labels.
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
          supportedLocales: AppLocalizations.supportedLocales,
          localizationsDelegates: const [
            AppLocalizations.delegate,
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
        File(
          'lib/features/station/radio/presentation/live_screen.dart',
        ).readAsStringSync() +
        File(
          'lib/features/station/radio/presentation/widgets/live_feed.dart',
        ).readAsStringSync();

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
