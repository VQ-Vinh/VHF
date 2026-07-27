import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/models/plan_entitlements.dart';

void main() {
  test('Free defaults limit live logs and unlock history next day', () {
    final policy = PlanEntitlements.fromAccount(const {});
    expect(policy.liveLogLimit, 10);
    expect(policy.historyUnlockDelayDays, 1);
    expect(policy.maxConcurrency, 2);

    final result = DateTime(2026, 7, 23, 23, 59);
    expect(
      policy.historyIsUnlocked(result, DateTime(2026, 7, 23, 23, 59, 59)),
      isFalse,
    );
    expect(policy.historyIsUnlocked(result, DateTime(2026, 7, 24)), isTrue);
  });

  test('zero limits mean unrestricted live and history access', () {
    final policy = PlanEntitlements.fromAccount(const {
      'entitlements': {
        'live_log_limit': 0,
        'history_unlock_delay_days': 0,
        'max_concurrency': 3,
      },
    });
    expect(policy.firestoreLiveLimit, isNull);
    expect(policy.maxConcurrency, 3);
    expect(
      policy.historyIsUnlocked(
        DateTime(2026, 7, 23, 12),
        DateTime(2026, 7, 23, 12),
      ),
      isTrue,
    );
  });
}
