import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/features/pairing/pairing_screen.dart';

void main() {
  test('fixed device label deep link is parsed', () {
    final link = parsePairingLink(
      Uri.parse(
        'prana-elex:///activate?v=1&id=ABCDEFGH23&code=ABCDEFGH23456789',
      ),
    );
    expect(link?.mode, PairingMode.label);
    expect(link?.identifier, 'ABCDEFGH23');
    expect(link?.code, 'ABCDEFGH23456789');
  });

  test('legacy temporary pairing remains supported', () {
    final link = parsePairingLink(
      Uri.parse('prana-elex:///pair?pairing_id=pair-1&code=ABCDEFGH'),
    );
    expect(link?.mode, PairingMode.temporary);
    expect(link?.identifier, 'pair-1');
    expect(link?.code, 'ABCDEFGH');
  });

  test('foreign QR link is rejected', () {
    expect(parsePairingLink(Uri.parse('https://example.com/activate')), isNull);
  });
}
