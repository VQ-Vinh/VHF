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
    this.detectedLanguage = '',
    this.translationOriginal = '',
    this.translationEdited = false,
    this.audioFilename = '',
    this.outputAvailable = false,
    this.attempt = 1,
    this.createdAt,
  });

  final String id;
  final String stationId;
  final Duration duration;
  final String targetLanguage;
  final String transcript;
  final String translation;
  final String status;
  final String? error;
  final String detectedLanguage;
  final String translationOriginal;
  final bool translationEdited;
  final String audioFilename;
  final bool outputAvailable;
  final int attempt;
  final DateTime? createdAt;

  factory TxDraft.fromMap(Map<String, dynamic> map) => TxDraft(
    id: map['id'] as String,
    stationId: map['station_id'] as String,
    duration: Duration(milliseconds: map['duration_ms'] as int? ?? 0),
    targetLanguage: map['target_language'] as String? ?? 'vi',
    transcript: map['transcript'] as String? ?? '',
    translation: map['translation'] as String? ?? '',
    status: map['status'] as String? ?? 'review_ready',
    error: map['error'] as String?,
    detectedLanguage: map['detected_language'] as String? ?? '',
    translationOriginal: map['translation_original'] as String? ?? '',
    translationEdited: map['translation_edited'] as bool? ?? false,
    audioFilename: map['audio_filename'] as String? ?? '',
    outputAvailable: map['output_available'] as bool? ?? false,
    attempt: map['attempt'] as int? ?? 1,
    createdAt: DateTime.tryParse(map['created_at'] as String? ?? ''),
  );

  TxDraft copyWith({String? translation, String? status}) => TxDraft(
    id: id,
    stationId: stationId,
    duration: duration,
    targetLanguage: targetLanguage,
    transcript: transcript,
    translation: translation ?? this.translation,
    status: status ?? this.status,
    error: error,
    detectedLanguage: detectedLanguage,
    translationOriginal: translationOriginal,
    translationEdited: translationEdited,
    audioFilename: audioFilename,
    outputAvailable: outputAvailable,
    attempt: attempt,
    createdAt: createdAt,
  );
}
