class TxRecordingInput {
  const TxRecordingInput({
    required this.stationId,
    required this.duration,
    required this.targetLanguage,
  });

  final String stationId;
  final Duration duration;
  final String targetLanguage;
}

class TxDraft {
  const TxDraft({
    required this.id,
    required this.stationId,
    required this.duration,
    required this.targetLanguage,
    required this.transcript,
    required this.translation,
  });

  final String id;
  final String stationId;
  final Duration duration;
  final String targetLanguage;
  final String transcript;
  final String translation;
}
