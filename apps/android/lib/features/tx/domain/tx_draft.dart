class TxRecordingInput {
  const TxRecordingInput({
    required this.stationId,
    required this.duration,
    required this.targetLanguage,
    this.audioPath,
  });

  final String stationId;
  final Duration duration;
  final String targetLanguage;
  final String? audioPath;
}

class TxDraft {
  const TxDraft({
    required this.id,
    required this.stationId,
    required this.duration,
    required this.targetLanguage,
    required this.transcript,
    required this.translation,
    this.status = 'review_ready',
    this.error,
  });

  final String id;
  final String stationId;
  final Duration duration;
  final String targetLanguage;
  final String transcript;
  final String translation;
  final String status;
  final String? error;

  factory TxDraft.fromMap(Map<String, dynamic> map) => TxDraft(
    id: map['id'] as String,
    stationId: map['station_id'] as String,
    duration: Duration(milliseconds: map['duration_ms'] as int? ?? 0),
    targetLanguage: map['target_language'] as String? ?? 'vi',
    transcript: map['transcript'] as String? ?? '',
    translation: map['translation'] as String? ?? '',
    status: map['status'] as String? ?? 'review_ready',
    error: map['error'] as String?,
  );
}
