import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/core/localization.dart';
import 'package:prana_mobile/core/theme.dart';
import 'package:prana_mobile/features/account/account_screen.dart';

void main() {
  Widget harness({
    String stationCode = 'VINH_0f90cd8e',
    VoidCallback? onCopyCode,
    VoidCallback? onRemove,
  }) => MaterialApp(
    theme: PranaTheme.light(),
    locale: const Locale('vi'),
    supportedLocales: AppText.supportedLocales,
    localizationsDelegates: const [
      GlobalMaterialLocalizations.delegate,
      GlobalWidgetsLocalizations.delegate,
      GlobalCupertinoLocalizations.delegate,
    ],
    home: Scaffold(
      body: StationAccountTile(
        stationId: 'station-1',
        name: 'VINH',
        platform: 'linux',
        stationCode: stationCode,
        onCopyCode: onCopyCode,
        onRemove: onRemove ?? () {},
      ),
    ),
  );

  testWidgets('owners read and copy the code support asks for', (tester) async {
    final copied = <MethodCall>[];
    tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
      SystemChannels.platform,
      (call) async {
        if (call.method == 'Clipboard.setData') copied.add(call);
        return null;
      },
    );
    addTearDown(
      () => tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
        SystemChannels.platform,
        null,
      ),
    );

    await tester.pumpWidget(
      harness(
        onCopyCode:
            () => Clipboard.setData(
              const ClipboardData(text: 'VINH_0f90cd8e'),
            ),
      ),
    );

    expect(find.text('VINH'), findsOneWidget);
    expect(find.text('linux'), findsOneWidget);
    expect(find.text('VINH_0f90cd8e'), findsOneWidget);

    await tester.tap(
      find.byKey(const ValueKey('station-code-copy-station-1')),
    );
    await tester.pumpAndSettle();

    expect(copied, hasLength(1));
    expect(copied.single.arguments['text'], 'VINH_0f90cd8e');
  });

  testWidgets('a Station that has never beaten offers nothing to copy', (
    tester,
  ) async {
    await tester.pumpWidget(harness(stationCode: ''));

    expect(
      find.byKey(const ValueKey('station-code-copy-station-1')),
      findsNothing,
    );
    expect(find.byIcon(Icons.copy_outlined), findsNothing);
  });

  testWidgets('the copy action never crowds out unpairing', (tester) async {
    for (final code in const ['VINH_0f90cd8e', '']) {
      var removed = 0;
      await tester.pumpWidget(
        harness(stationCode: code, onRemove: () => removed++),
      );

      final remove = find.byKey(const ValueKey('station-remove-station-1'));
      expect(remove, findsOneWidget, reason: 'code="$code"');
      await tester.tap(remove);
      await tester.pump();
      expect(removed, 1, reason: 'code="$code"');
      expect(tester.takeException(), isNull);
    }
  });
}
