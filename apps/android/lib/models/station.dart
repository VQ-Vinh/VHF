import 'package:cloud_firestore/cloud_firestore.dart';

class DesiredState {
  const DesiredState({
    required this.running,
    required this.targetLanguage,
    required this.retryGeneration,
    required this.generation,
  });

  final bool running;
  final String targetLanguage;
  final int retryGeneration;
  final int generation;

  factory DesiredState.fromMap(Map<String, dynamic> map) => DesiredState(
    running: map['running'] as bool? ?? false,
    targetLanguage: map['target_language'] as String? ?? 'en',
    retryGeneration: map['retry_generation'] as int? ?? 0,
    generation: map['generation'] as int? ?? 0,
  );
}

class StationModel {
  const StationModel({
    required this.id,
    required this.name,
    required this.platform,
    required this.active,
    required this.captureState,
    required this.desired,
    required this.observedGeneration,
    required this.sessionId,
    required this.sequence,
    required this.lastSeenAt,
    this.lastError,
  });

  final String id;
  final String name;
  final String platform;
  final bool active;
  final String captureState;
  final DesiredState desired;
  final int observedGeneration;
  final String sessionId;
  final int sequence;
  final DateTime? lastSeenAt;
  final String? lastError;

  bool isOnlineAt(DateTime now) =>
      active &&
      lastSeenAt != null &&
      now.difference(lastSeenAt!).inSeconds <= 15;
  bool get isOnline => isOnlineAt(DateTime.now());
  bool get commandPending => observedGeneration < desired.generation;

  factory StationModel.fromDocument(
    DocumentSnapshot<Map<String, dynamic>> doc,
  ) {
    final map = doc.data() ?? const <String, dynamic>{};
    return StationModel(
      id: doc.id,
      name: map['name'] as String? ?? 'PRANA station',
      platform: map['platform'] as String? ?? 'Unknown',
      active: map['active'] as bool? ?? true,
      captureState: map['capture_state'] as String? ?? 'idle',
      desired: DesiredState.fromMap(
        Map<String, dynamic>.from(map['desired_state'] as Map? ?? const {}),
      ),
      observedGeneration: map['observed_generation'] as int? ?? 0,
      sessionId: map['session_id'] as String? ?? '',
      sequence: map['sequence'] as int? ?? 0,
      lastSeenAt: (map['last_seen_at'] as Timestamp?)?.toDate(),
      lastError: map['last_error'] as String?,
    );
  }
}

class TranslationResult {
  const TranslationResult({
    required this.requestId,
    required this.sequence,
    required this.transcript,
    required this.translation,
    required this.language,
    required this.confidence,
    required this.timestamp,
    this.error,
  });

  final String requestId;
  final int sequence;
  final String transcript;
  final String translation;
  final String language;
  final double confidence;
  final DateTime timestamp;
  final String? error;

  factory TranslationResult.fromDocument(
    DocumentSnapshot<Map<String, dynamic>> doc,
  ) {
    final map = doc.data() ?? const <String, dynamic>{};
    return TranslationResult(
      requestId: map['request_id'] as String? ?? doc.id,
      sequence: map['sequence'] as int? ?? 0,
      transcript: map['transcript_restored'] as String? ?? '',
      translation: map['translation'] as String? ?? '',
      language: map['detected_language'] as String? ?? '',
      confidence: (map['confidence'] as num?)?.toDouble() ?? 0,
      timestamp: _dateTime(map['timestamp']) ?? DateTime.now(),
      error: map['error'] as String?,
    );
  }

  static DateTime? _dateTime(Object? value) {
    if (value is Timestamp) return value.toDate();
    if (value is String) return DateTime.tryParse(value);
    return null;
  }
}
