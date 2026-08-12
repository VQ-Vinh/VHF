class PlanEntitlements {
  const PlanEntitlements({
    required this.liveLogLimit,
    required this.historyUnlockDelayDays,
    required this.maxConcurrency,
    required this.txMaxRecordingSeconds,
  });

  final int liveLogLimit;
  final int historyUnlockDelayDays;
  final int maxConcurrency;
  final int txMaxRecordingSeconds;

  int? get firestoreLiveLimit => liveLogLimit <= 0 ? null : liveLogLimit;

  factory PlanEntitlements.fromAccount(Map<String, dynamic> account) {
    final values = Map<String, dynamic>.from(
      account['entitlements'] as Map? ?? const {},
    );
    return PlanEntitlements(
      liveLogLimit: (values['live_log_limit'] as num?)?.toInt() ?? 10,
      historyUnlockDelayDays:
          (values['history_unlock_delay_days'] as num?)?.toInt() ?? 1,
      maxConcurrency: (values['max_concurrency'] as num?)?.toInt() ?? 2,
      txMaxRecordingSeconds:
          (values['tx_max_recording_seconds'] as num?)?.toInt() ?? 60,
    );
  }

  DateTime unlockAt(DateTime timestamp) {
    final local = timestamp.toLocal();
    return DateTime(
      local.year,
      local.month,
      local.day + historyUnlockDelayDays,
    );
  }

  bool historyIsUnlocked(DateTime timestamp, DateTime now) =>
      !now.isBefore(unlockAt(timestamp));
}
