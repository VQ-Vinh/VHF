import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/providers.dart';
import 'package:prana_mobile/services/prana_api.dart';

void main() {
  test('polling recovers after an initial connection failure', () async {
    var attempt = 0;
    final stream = resilientPoll<int>(
      fetch: () async {
        attempt++;
        if (attempt == 1) {
          throw const PranaApiFailure('error_api_unreachable');
        }
        return attempt;
      },
      pollInterval: const Duration(milliseconds: 1),
      initialRetryDelay: const Duration(milliseconds: 1),
      maxRetryDelay: const Duration(milliseconds: 2),
    );

    await expectLater(
      stream,
      emitsInOrder([emitsError(isA<PranaApiFailure>()), 2]),
    );
  });

  test('polling keeps the last data state during a later failure', () async {
    var attempt = 0;
    final stream = resilientPoll<int>(
      fetch: () async {
        attempt++;
        if (attempt == 2) {
          throw const PranaApiFailure('error_api_unreachable');
        }
        return attempt;
      },
      pollInterval: const Duration(milliseconds: 1),
      initialRetryDelay: const Duration(milliseconds: 1),
      maxRetryDelay: const Duration(milliseconds: 2),
    );

    await expectLater(stream, emitsInOrder([1, 3]));
  });
}
