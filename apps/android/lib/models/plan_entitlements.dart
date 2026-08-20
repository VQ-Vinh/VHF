class PlanEntitlements {
  const PlanEntitlements({
    required this.historyPastDays,
    required this.maxConcurrency,
    required this.txMaxRecordingSeconds,
  });

  /// Days before today that stay readable. 0 means today only.
  final int historyPastDays;
  final int maxConcurrency;
  final int txMaxRecordingSeconds;

  factory PlanEntitlements.fromAccount(Map<String, dynamic> account) {
    final values = Map<String, dynamic>.from(
      account['entitlements'] as Map? ?? const {},
    );
    return PlanEntitlements(
      historyPastDays: (values['history_past_days'] as num?)?.toInt() ?? 0,
      maxConcurrency: (values['max_concurrency'] as num?)?.toInt() ?? 2,
      txMaxRecordingSeconds:
          (values['tx_max_recording_seconds'] as num?)?.toInt() ?? 60,
    );
  }

  /// Oldest day still readable under this plan.
  DateTime earliestReadableDay(DateTime now) {
    final local = now.toLocal();
    return DateTime(local.year, local.month, local.day - historyPastDays);
  }

  bool historyIsUnlocked(DateTime timestamp, DateTime now) {
    final local = timestamp.toLocal();
    final day = DateTime(local.year, local.month, local.day);
    return !day.isBefore(earliestReadableDay(now));
  }
}
