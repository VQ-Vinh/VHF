import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/core/responsive.dart';
import 'package:prana_mobile/core/theme.dart';
import 'package:prana_mobile/core/widgets.dart';

/// The brand mark lives inside ResponsiveHeader, so every header carries it
/// without each screen remembering to add one. That puts a fixed-width element
/// into rows that were already tight -- the live header overflowed by 9.3px the
/// first time it went in -- so the width and text-scale matrix from AGENTS.md
/// is pinned here rather than left to whichever screen happens to be tested.
void main() {
  const mark = ValueKey('prana-logo-mark');

  Widget harness({
    required Size size,
    required double textScale,
    required Widget header,
  }) => MaterialApp(
    theme: PranaTheme.light(),
    // MediaQuery has to wrap the app's own subtree, not replace it from
    // `home`, or the header lays out unbounded and the action sizes to
    // infinity. Same shape as live_layout_test.
    builder:
        (context, child) => MediaQuery(
          data: MediaQueryData(
            size: size,
            textScaler: TextScaler.linear(textScale),
          ),
          child: child!,
        ),
    home: ResponsiveScaffold(appBar: header, body: const SizedBox.shrink()),
  );

  for (final width in <double>[320, 375, 390, 400, 430, 768, 1024]) {
    for (final textScale in <double>[1.0, 1.5, 2.0]) {
      testWidgets('header keeps its mark at ${width}px, text $textScale', (
        tester,
      ) async {
        tester.view.physicalSize = Size(width, 800);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);

        await tester.pumpWidget(
          harness(
            size: Size(width, 800),
            textScale: textScale,
            // An action with real intrinsic width, like the live header's
            // START control, is what makes the row compete for space.
            header: ResponsiveHeader(
              automaticallyImplyLeading: false,
              title: const Text('Trạm ven biển Nha Trang'),
              actions: const [
                SizedBox(
                  width: 108,
                  height: 44,
                  child: Center(child: Text('BẮT ĐẦU')),
                ),
              ],
            ),
          ),
        );

        expect(find.byKey(mark), findsOneWidget);
        expect(tester.takeException(), isNull);
      });
    }
  }

  testWidgets('PranaPageHeader shows the mark once, not twice', (tester) async {
    await tester.pumpWidget(
      harness(
        size: const Size(390, 800),
        textScale: 1,
        header: const PranaPageHeader(title: 'Tài khoản'),
      ),
    );

    // PranaPageHeader used to draw its own mark on top of the one the shared
    // header now provides.
    expect(find.byKey(mark), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
