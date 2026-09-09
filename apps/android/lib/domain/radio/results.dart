class TranslationResult {
  const TranslationResult({
    required this.requestId,
    this.sessionId = '',
    required this.sequence,
    required this.transcript,
    required this.translation,
    required this.language,
    this.targetLanguage,
    required this.confidence,
    required this.timestamp,
    this.error,
  });

  final String requestId;
  final String sessionId;
  final int sequence;
  final String transcript;
  final String translation;
  final String language;
  final String? targetLanguage;
  final double confidence;
  final DateTime timestamp;
  final String? error;

  factory TranslationResult.fromMap(
    Map<String, dynamic> map, {
    String fallbackId = '',
  }) {
    return TranslationResult(
      requestId: map['request_id'] as String? ?? fallbackId,
      sessionId: map['session_id'] as String? ?? '',
      sequence: map['sequence'] as int? ?? 0,
      transcript: map['transcript_restored'] as String? ?? '',
      translation: map['translation'] as String? ?? '',
      language: map['detected_language'] as String? ?? '',
      targetLanguage: map['target_language'] as String?,
      confidence: (map['confidence'] as num?)?.toDouble() ?? 0,
      timestamp: _dateTime(map['timestamp']) ?? DateTime.now(),
      error: map['error'] as String?,
    );
  }

  static DateTime? _dateTime(Object? value) {
    if (value is DateTime) return value;
    if (value is String) return DateTime.tryParse(value);
    return null;
  }
}

String localDateKey(DateTime value) {
  final local = value.toLocal();
  return '${local.year.toString().padLeft(4, '0')}-'
      '${local.month.toString().padLeft(2, '0')}-'
      '${local.day.toString().padLeft(2, '0')}';
}

class StationHistoryDay {
  const StationHistoryDay({
    required this.date,
    required this.resultCount,
    required this.firstResultAt,
    required this.lastResultAt,
    required this.locked,
  });

  final DateTime date;
  final int resultCount;
  final DateTime firstResultAt;
  final DateTime lastResultAt;
  final bool locked;

  String get apiDate =>
      '${date.year.toString().padLeft(4, '0')}-'
      '${date.month.toString().padLeft(2, '0')}-'
      '${date.day.toString().padLeft(2, '0')}';

  factory StationHistoryDay.fromMap(Map<String, dynamic> map) {
    final parts = (map['date'] as String? ?? '').split('-');
    final day =
        parts.length == 3
            ? DateTime(
              int.parse(parts[0]),
              int.parse(parts[1]),
              int.parse(parts[2]),
            )
            : DateTime.now();
    return StationHistoryDay(
      date: day,
      resultCount: (map['result_count'] as num?)?.toInt() ?? 0,
      firstResultAt: TranslationResult._dateTime(map['first_result_at']) ?? day,
      lastResultAt: TranslationResult._dateTime(map['last_result_at']) ?? day,
      locked: map['locked'] as bool? ?? true,
    );
  }
}

int compareTranslationChronologically(
  TranslationResult left,
  TranslationResult right,
) {
  final byTime = left.timestamp.compareTo(right.timestamp);
  if (byTime != 0) return byTime;
  final bySequence = left.sequence.compareTo(right.sequence);
  if (bySequence != 0) return bySequence;
  return left.requestId.compareTo(right.requestId);
}

List<TranslationResult> liveTranslationsForLocalDay(
  Iterable<TranslationResult> results,
  DateTime now,
) {
  final today = now.toLocal();
  return results.where((result) {
    final timestamp = result.timestamp.toLocal();
    return timestamp.year == today.year &&
        timestamp.month == today.month &&
        timestamp.day == today.day;
  }).toList();
}
