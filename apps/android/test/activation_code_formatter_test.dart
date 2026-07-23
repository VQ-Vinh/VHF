import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/features/pairing/pairing_screen.dart';

void main() {
  const completeCode = 'ABCD EFGH JKMP QRST';

  test('accepts all 16 activation characters when typed', () {
    final formatter = ActivationCodeInputFormatter();
    var value = TextEditingValue.empty;

    for (final character in 'ABCDEFGHJKMPQRST'.split('')) {
      final nextText = '${value.text}$character';
      value = formatter.formatEditUpdate(
        value,
        TextEditingValue(
          text: nextText,
          selection: TextSelection.collapsed(offset: nextText.length),
        ),
      );
    }

    expect(value.text, completeCode);
  });

  test('normalizes a pasted activation code and ignores extra spaces', () {
    final formatter = ActivationCodeInputFormatter();
    const pasted = 'abcd  efgh   jkmp qrst';

    final value = formatter.formatEditUpdate(
      TextEditingValue.empty,
      const TextEditingValue(
        text: pasted,
        selection: TextSelection.collapsed(offset: pasted.length),
      ),
    );

    expect(value.text, completeCode);
  });

  test('does not accept more than 16 raw characters', () {
    final formatter = ActivationCodeInputFormatter();
    const pasted = 'ABCDEFGHJKMPQRSTEXTRA';

    final value = formatter.formatEditUpdate(
      TextEditingValue.empty,
      const TextEditingValue(
        text: pasted,
        selection: TextSelection.collapsed(offset: pasted.length),
      ),
    );

    expect(value.text, completeCode);
  });
}
