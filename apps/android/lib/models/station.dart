import 'package:cloud_firestore/cloud_firestore.dart';

class DesiredState {
  const DesiredState({
    required this.running,
    required this.targetLanguage,
    required this.retryGeneration,
    this.captureMode = 'device',
    this.audioDeviceId = '',
    this.capabilityRefreshGeneration = 0,
    required this.generation,
  });

  final bool running;
  final String targetLanguage;
  final int retryGeneration;
  final String captureMode;
  final String audioDeviceId;
  final int capabilityRefreshGeneration;
  final int generation;

  factory DesiredState.fromMap(Map<String, dynamic> map) => DesiredState(
    running: map['running'] as bool? ?? false,
    targetLanguage: map['target_language'] as String? ?? 'en',
    retryGeneration: map['retry_generation'] as int? ?? 0,
    captureMode: map['capture_mode'] as String? ?? 'device',
    audioDeviceId: map['audio_device_id'] as String? ?? '',
    capabilityRefreshGeneration:
        map['capability_refresh_generation'] as int? ?? 0,
    generation: map['generation'] as int? ?? 0,
  );
}

class StationAudioDevice {
  const StationAudioDevice({
    required this.id,
    required this.name,
    required this.mode,
    required this.inputChannels,
    required this.outputChannels,
    required this.sampleRate,
    required this.hostApi,
  });

  final String id;
  final String name;
  final String mode;
  final int inputChannels;
  final int outputChannels;
  final int sampleRate;
  final String hostApi;

  factory StationAudioDevice.fromMap(Map<String, dynamic> map) =>
      StationAudioDevice(
        id: map['id'] as String? ?? '',
        name: map['name'] as String? ?? 'Audio device',
        mode: map['mode'] as String? ?? 'device',
        inputChannels: map['input_channels'] as int? ?? 0,
        outputChannels: map['output_channels'] as int? ?? 0,
        sampleRate: map['sample_rate'] as int? ?? 0,
        hostApi: map['host_api'] as String? ?? '',
      );
}

class StationCapabilities {
  const StationCapabilities({
    required this.capabilityHash,
    required this.captureModes,
    required this.audioDevices,
    required this.storagePath,
    this.updatedAt,
  });

  final String capabilityHash;
  final List<String> captureModes;
  final List<StationAudioDevice> audioDevices;
  final String storagePath;
  final DateTime? updatedAt;

  factory StationCapabilities.fromMap(Map<String, dynamic> map) =>
      StationCapabilities(
        capabilityHash: map['capability_hash'] as String? ?? '',
        captureModes: List<String>.from(
          map['capture_modes'] as List? ?? const ['device'],
        ),
        audioDevices:
            (map['audio_devices'] as List? ?? const [])
                .map(
                  (item) => StationAudioDevice.fromMap(
                    Map<String, dynamic>.from(item as Map),
                  ),
                )
                .toList(),
        storagePath: map['storage_path'] as String? ?? '',
        updatedAt: _dateTime(map['updated_at']),
      );

  static DateTime? _dateTime(Object? value) {
    if (value is Timestamp) return value.toDate();
    if (value is String) return DateTime.tryParse(value);
    return null;
  }
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
    this.capabilities,
    this.activeCaptureMode = 'device',
    this.activeAudioDeviceId = '',
    this.retrying = false,
    this.retryCode,
    this.retryAttempt = 0,
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
  final StationCapabilities? capabilities;
  final String activeCaptureMode;
  final String activeAudioDeviceId;
  final bool retrying;
  final String? retryCode;
  final int retryAttempt;

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
      capabilities:
          map['capabilities'] is Map
              ? StationCapabilities.fromMap(
                Map<String, dynamic>.from(map['capabilities'] as Map),
              )
              : null,
      activeCaptureMode: map['active_capture_mode'] as String? ?? 'device',
      activeAudioDeviceId: map['active_audio_device_id'] as String? ?? '',
      retrying: map['retrying'] as bool? ?? false,
      retryCode: map['retry_code'] as String?,
      retryAttempt: map['retry_attempt'] as int? ?? 0,
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
    this.targetLanguage,
    required this.confidence,
    required this.timestamp,
    this.error,
  });

  final String requestId;
  final int sequence;
  final String transcript;
  final String translation;
  final String language;
  final String? targetLanguage;
  final double confidence;
  final DateTime timestamp;
  final String? error;

  factory TranslationResult.fromDocument(
    DocumentSnapshot<Map<String, dynamic>> doc,
  ) => TranslationResult.fromMap(
    doc.data() ?? const <String, dynamic>{},
    fallbackId: doc.id,
  );

  factory TranslationResult.fromMap(
    Map<String, dynamic> map, {
    String fallbackId = '',
  }) {
    return TranslationResult(
      requestId: map['request_id'] as String? ?? fallbackId,
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
    if (value is Timestamp) return value.toDate();
    if (value is String) return DateTime.tryParse(value);
    return null;
  }
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
