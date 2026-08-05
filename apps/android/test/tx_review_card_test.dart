import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/features/tx/domain/tx_draft.dart';
import 'package:prana_mobile/features/tx/presentation/widgets/tx_review_card.dart';

void main() {
  const draft = TxDraft(
    id: 'tx-1',
    stationId: 'station-1',
    duration: Duration(seconds: 2),
    targetLanguage: 'vi',
    transcript: 'Switch to channel eighteen.',
    translation: 'Chuyển sang kênh mười tám.',
  );

  Widget harness(ValueChanged<String> onTransmit) => MaterialApp(
    locale: const Locale('en'),
    home: Scaffold(
      body: TxReviewCard(
        draft: draft,
        languageLabel: 'Vietnamese',
        onTransmit: onTransmit,
        onCancel: () {},
      ),
    ),
  );

  testWidgets('translation can be edited while transcript stays read-only', (
    tester,
  ) async {
    String? submitted;
    await tester.pumpWidget(harness((value) => submitted = value));

    expect(find.text(draft.transcript), findsOneWidget);
    expect(find.byType(SelectableText), findsOneWidget);
    await tester.enterText(
      find.byKey(const ValueKey('tx-translation-editor')),
      '  Nội dung cuối đã sửa.  ',
    );
    await tester.tap(find.byKey(const ValueKey('tx-confirm-button')));

    expect(submitted, 'Nội dung cuối đã sửa.');
  });

  testWidgets('blank translation cannot be transmitted', (tester) async {
    var submitted = false;
    await tester.pumpWidget(harness((_) => submitted = true));

    await tester.enterText(
      find.byKey(const ValueKey('tx-translation-editor')),
      '   ',
    );
    await tester.pump();

    final button = tester.widget<FilledButton>(
      find.byKey(const ValueKey('tx-confirm-button')),
    );
    expect(button.onPressed, isNull);
    expect(submitted, isFalse);
  });
}
