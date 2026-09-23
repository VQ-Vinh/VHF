import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/core/service_messages.dart';
import 'package:prana_mobile/core/theme.dart';
import 'package:prana_mobile/core/widgets.dart';
import 'package:prana_mobile/l10n/app_localizations.dart';

const _sizes = [
  Size(320, 640),
  Size(375, 812),
  Size(390, 844),
  Size(400, 800),
  Size(430, 932),
  Size(768, 1024),
  Size(1024, 1366),
  Size(1440, 900),
  // Short landscape phone.
  Size(740, 320),
];

Future<void> _pump(
  WidgetTester tester, {
  required Size size,
  required Locale locale,
  required double textScale,
  required ThemeData theme,
  required Widget Function(BuildContext) body,
}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    MaterialApp(
      theme: theme,
      locale: locale,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      builder:
          (context, child) => MediaQuery(
            data: MediaQuery.of(
              context,
            ).copyWith(textScaler: TextScaler.linear(textScale)),
            child: child!,
          ),
      home: Scaffold(body: Builder(builder: body)),
    ),
  );
  await tester.pump();
}

void _expectInsideViewport(WidgetTester tester, Finder finder, Size size) {
  for (final element in finder.evaluate()) {
    final box = element.renderObject! as RenderBox;
    final rect = box.localToGlobal(Offset.zero) & box.size;
    expect(rect.left, greaterThanOrEqualTo(0));
    expect(rect.right, lessThanOrEqualTo(size.width + 0.5));
  }
}

void main() {
  for (final locale in const [Locale('vi'), Locale('en')]) {
    for (final textScale in const [1.0, 1.5, 2.0]) {
      for (final theme in [PranaTheme.light(), PranaTheme.dark()]) {
        final label =
            '${locale.languageCode} x$textScale ${theme.brightness.name}';

        testWidgets('ErrorState fits every viewport ($label)', (tester) async {
          for (final size in _sizes) {
            await _pump(
              tester,
              size: size,
              locale: locale,
              textScale: textScale,
              theme: theme,
              body:
                  (context) => ErrorState(
                    title: AppLocalizations.of(context).loadFailedTitle,
                    message: localizedServiceMessage(
                      context,
                      'error_service_unavailable',
                    ),
                    retryLabel: AppLocalizations.of(context).retry,
                    onRetry: () {},
                  ),
            );
            expect(tester.takeException(), isNull, reason: '$size');
            _expectInsideViewport(tester, find.byType(FilledButton), size);
          }
        });

        testWidgets('NoticeCard with actions wraps ($label)', (tester) async {
          for (final size in _sizes) {
            await _pump(
              tester,
              size: size,
              locale: locale,
              textScale: textScale,
              theme: theme,
              body:
                  (context) => SingleChildScrollView(
                    padding: const EdgeInsets.all(16),
                    child: NoticeCard(
                      message: localizedServiceMessage(
                        context,
                        'rx_audio_input_not_found',
                      ),
                      actions: [
                        TextButton(
                          onPressed: () {},
                          child: Text(AppLocalizations.of(context).retry),
                        ),
                        TextButton(
                          onPressed: () {},
                          child: Text(AppLocalizations.of(context).stop),
                        ),
                        TextButton(
                          onPressed: () {},
                          child: Text(AppLocalizations.of(context).close),
                        ),
                      ],
                    ),
                  ),
            );
            expect(tester.takeException(), isNull, reason: '$size');
            _expectInsideViewport(tester, find.byType(TextButton), size);
          }
        });
      }
    }
  }

  testWidgets('NoticeCard is announced to screen readers', (tester) async {
    await _pump(
      tester,
      size: const Size(390, 844),
      locale: const Locale('vi'),
      textScale: 1,
      theme: PranaTheme.light(),
      body: (context) => const NoticeCard(message: 'x'),
    );
    final semantics = tester.getSemantics(find.byType(NoticeCard));
    expect(semantics.flagsCollection.isLiveRegion, isTrue);
  });
}
