import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/app/di/auth_providers.dart';
import 'package:prana_mobile/app/navigation/router.dart';
import 'package:prana_mobile/preview/demo_store.dart';
import 'package:prana_mobile/preview/preview_app.dart';
import 'preview_test.dart' show frames, containerOf;

void main() {
  for (final size in [
    for (final width in [320, 375, 390, 400, 430, 768, 1024, 1920])
      Size(width.toDouble(), 800),
    const Size(800, 360),
  ]) {
    testWidgets(
      'preview routes responsive at $size, EN/VI, light/dark, 1/1.5/2',
      (tester) async {
        tester.view.physicalSize = size;
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        final store = DemoStore(ticking: false);
        await tester.pumpWidget(PreviewSession(onReset: () {}, store: store));
        await frames(tester);
        final container = containerOf(tester);
        final router = container.read(routerProvider);
        for (final language in ['en', 'vi']) {
          await container.read(appLocaleProvider).setLocale(language);
          for (final dark in [false, true]) {
            await container.read(appThemeModeProvider).setDarkMode(dark);
            for (final scale in [1.0, 1.5, 2.0]) {
              for (final path in [
                '/stations',
                '/stations/demo-online/control',
                '/stations/demo-online/live',
                '/stations/demo-online/history',
                '/stations/demo-online/settings',
                '/account',
              ]) {
                router.go(path);
                await frames(tester, 4);
                expect(
                  tester.takeException(),
                  isNull,
                  reason: '$path $size $language dark=$dark scale=$scale',
                );
                for (final element in find.byType(RichText).evaluate()) {
                  final paragraph = element.renderObject;
                  if (paragraph is RenderParagraph && paragraph.attached) {
                    expect(
                      paragraph.didExceedMaxLines,
                      isFalse,
                      reason:
                          'Clipped "${paragraph.text.toPlainText()}" at $path $size $language $scale',
                    );
                  }
                }
              }
              await tester.tap(
                find.byKey(const ValueKey('preview-text-scale')),
              );
              await frames(tester, 2);
            }
          }
        }
        expect(store.commandCount, 0);
        await tester.pumpWidget(const SizedBox.shrink());
        await tester.pump();
        expect(store.projectionSubscriptions, 0);
        expect(store.resultsSubscriptions, 0);
      },
    );
  }
}
