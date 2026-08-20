import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/models/plan_entitlements.dart';

void main() {
  test('Free defaults expose today and lock every earlier day', () {
    final policy = PlanEntitlements.fromAccount(const {});
    expect(policy.historyPastDays, 0);
    expect(policy.maxConcurrency, 2);

    final now = DateTime(2026, 7, 23, 12);
    expect(
      policy.historyIsUnlocked(DateTime(2026, 7, 23, 0, 1), now),
      isTrue,
    );
    expect(
      policy.historyIsUnlocked(DateTime(2026, 7, 22, 23, 59), now),
      isFalse,
    );
  });

  test('a past-day window opens exactly that many days back', () {
    final policy = PlanEntitlements.fromAccount(const {
      'entitlements': {'history_past_days': 7, 'max_concurrency': 3},
    });
    expect(policy.maxConcurrency, 3);

    final now = DateTime(2026, 7, 23, 12);
    expect(policy.earliestReadableDay(now), DateTime(2026, 7, 16));
    expect(policy.historyIsUnlocked(DateTime(2026, 7, 16, 8), now), isTrue);
    expect(policy.historyIsUnlocked(DateTime(2026, 7, 15, 23), now), isFalse);
  });
}
