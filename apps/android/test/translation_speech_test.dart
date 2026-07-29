import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/models/station.dart';
import 'package:prana_mobile/services/source_audio.dart';
import 'package:prana_mobile/services/translation_speech.dart';

class FakeSpeechEngine implements SpeechEngine {
  final List<(String, String)> spoken = [];
  final List<String> unavailable = [];
  final Map<String, String> resolvedLocales = {};
  bool failAvailabilityCheck = false;
  int stopCalls = 0;

  @override
  Future<String?> resolveLocale(String locale) async {
    if (failAvailabilityCheck) throw StateError('TTS engine unavailable');
    if (unavailable.contains(locale)) return null;
    return resolvedLocales[locale] ?? locale;
  }

  @override
  Future<void> speak(String text, String locale) async {
    spoken.add((text, locale));
  }

  @override
  Future<void> stop() async {
    stopCalls++;
  }
}

class FakeSourceAudioEngine implements SourceAudioEngine {
  final List<(String, String, String)> played = [];
  final Set<String> failures = {};
  int stopCalls = 0;
  int clearCalls = 0;

  @override
  Future<void> play(
    String stationId,
    String sessionId,
    String requestId,
  ) async {
    if (failures.contains(requestId)) throw StateError('missing source audio');
    played.add((stationId, sessionId, requestId));
  }

  @override
  Future<void> stop() async {
    stopCalls++;
  }

  @override
  Future<void> clearCache() async {
    clearCalls++;
  }
}

TranslationResult result(
  String id,
  int sequence, {
  String translation = 'Bản dịch',
  String? targetLanguage = 'vi',
}) => TranslationResult(
  requestId: id,
  sequence: sequence,
  transcript: 'Source',
  translation: translation,
  language: 'en',
  targetLanguage: targetLanguage,
  confidence: 1,
  timestamp: DateTime.utc(2026, 7, 28, 12, 0, sequence),
);

Future<void> settleSpeech() async {
  for (var index = 0; index < 6; index++) {
    await Future<void>.delayed(Duration.zero);
  }
}

TranslationResult sameLanguageResult(String id, {String language = 'vi-VN'}) =>
    TranslationResult(
      requestId: id,
      sequence: 1,
      transcript: 'Xin chào.',
      translation: 'Xin chào.',
      language: language,
      targetLanguage: 'VI',
      confidence: 1,
      timestamp: DateTime.utc(2026, 7, 28, 12),
    );

void main() {
  test('same source and target language plays original audio', () async {
    final speech = FakeSpeechEngine();
    final source = FakeSourceAudioEngine();
    final controller = TranslationSpeechController(speech, source);
    controller.trackStation('station-1', '');
    controller.trackStation('station-1', 'session-1');

    controller.ingest([sameLanguageResult('source')], fallbackLanguage: 'vi');
    await settleSpeech();

    expect(source.played, [('station-1', 'session-1', 'source')]);
    expect(speech.spoken, isEmpty);
  });

  test(
    'source audio failure falls back to detected-language transcript',
    () async {
      final speech = FakeSpeechEngine();
      final source = FakeSourceAudioEngine()..failures.add('missing');
      final controller = TranslationSpeechController(speech, source);
      controller.trackStation('station-1', '');
      controller.trackStation('station-1', 'session-1');

      await controller.speakNow(
        sameLanguageResult('missing', language: 'vi_VN'),
      );
      await settleSpeech();

      expect(speech.spoken, [('Xin chào.', 'vi-VN')]);
    },
  );

  test('manual playback uses original audio for matching languages', () async {
    final speech = FakeSpeechEngine();
    final source = FakeSourceAudioEngine();
    final controller = TranslationSpeechController(speech, source);
    controller.trackStation('station-1', 'session-1');

    await controller.speakNow(sameLanguageResult('manual-source'));
    await settleSpeech();
    await controller.stopCurrent();

    expect(source.played, [('station-1', 'session-1', 'manual-source')]);
    expect(source.stopCalls, greaterThanOrEqualTo(2));
    expect(speech.spoken, isEmpty);
  });

  test(
    'baselines existing results then speaks unseen results once in order',
    () async {
      final engine = FakeSpeechEngine();
      final controller = TranslationSpeechController(
        engine,
        FakeSourceAudioEngine(),
      );
      controller.trackStation('station-1', 'session-1');
      controller.ingest([result('old', 1)], fallbackLanguage: 'en');

      controller.ingest([
        result('new-2', 3),
        result('new-1', 2),
      ], fallbackLanguage: 'en');
      await settleSpeech();
      controller.ingest([
        result('old', 1),
        result('new-1', 2),
        result('new-2', 3),
      ], fallbackLanguage: 'en');
      await settleSpeech();

      expect(engine.spoken, [('Bản dịch', 'vi-VN'), ('Bản dịch', 'vi-VN')]);
    },
  );

  test('background clears queue and resume baselines missed results', () async {
    final engine = FakeSpeechEngine();
    final controller = TranslationSpeechController(
      engine,
      FakeSourceAudioEngine(),
    );
    controller.trackStation('station-1', 'session-1');
    controller.ingest([result('old', 1)], fallbackLanguage: 'vi');

    await controller.setForeground(false);
    controller.ingest([result('missed', 2)], fallbackLanguage: 'vi');
    await controller.setForeground(true);
    controller.ingest([
      result('old', 1),
      result('missed', 2),
    ], fallbackLanguage: 'vi');
    controller.ingest([
      result('old', 1),
      result('missed', 2),
      result('next', 3),
    ], fallbackLanguage: 'vi');
    await settleSpeech();

    expect(engine.spoken, [('Bản dịch', 'vi-VN')]);
  });

  test('idle station speaks the first result of its future session', () async {
    final engine = FakeSpeechEngine();
    final controller = TranslationSpeechController(
      engine,
      FakeSourceAudioEngine(),
    );
    controller.trackStation('station-1', '');
    controller.trackStation('station-1', 'session-1');
    controller.ingest([result('first', 1)], fallbackLanguage: 'vi');
    await settleSpeech();

    expect(engine.spoken, [('Bản dịch', 'vi-VN')]);
  });

  test('manual playback uses fallback language and can be stopped', () async {
    final engine = FakeSpeechEngine();
    final controller = TranslationSpeechController(
      engine,
      FakeSourceAudioEngine(),
    );
    controller.trackStation('station-1', 'session-1');
    controller.ingest(const [], fallbackLanguage: 'ja');

    await controller.speakNow(result('manual', 1, targetLanguage: null));
    await settleSpeech();
    await controller.stopCurrent();

    expect(engine.spoken, [('Bản dịch', 'ja-JP')]);
    expect(controller.speakingRequestId, isNull);
    expect(engine.stopCalls, greaterThanOrEqualTo(2));
  });

  test('unavailable voice is skipped with a warning', () async {
    final engine = FakeSpeechEngine()..unavailable.add('ko-KR');
    final controller = TranslationSpeechController(
      engine,
      FakeSourceAudioEngine(),
    );
    controller.trackStation('station-1', 'session-1');
    controller.ingest(const [], fallbackLanguage: 'en');
    controller.ingest([
      result('new', 1, targetLanguage: 'ko'),
    ], fallbackLanguage: 'en');
    await settleSpeech();

    expect(engine.spoken, isEmpty);
    expect(controller.warningKey, 'tts_language_unavailable');
  });

  test(
    'compatible locale returned by the engine is used for playback',
    () async {
      final engine = FakeSpeechEngine()..resolvedLocales['vi-VN'] = 'vi_VN';
      final controller = TranslationSpeechController(
        engine,
        FakeSourceAudioEngine(),
      );
      controller.trackStation('station-1', '');
      controller.trackStation('station-1', 'session-1');
      controller.ingest([result('new', 1)], fallbackLanguage: 'vi');
      await settleSpeech();

      expect(engine.spoken, [('Bản dịch', 'vi_VN')]);
      expect(controller.warningKey, isNull);
    },
  );

  test('TTS engine failure is reported without escaping the queue', () async {
    final engine = FakeSpeechEngine()..failAvailabilityCheck = true;
    final controller = TranslationSpeechController(
      engine,
      FakeSourceAudioEngine(),
    );
    controller.trackStation('station-1', '');
    controller.trackStation('station-1', 'session-1');
    controller.ingest([result('new', 1)], fallbackLanguage: 'vi');
    await settleSpeech();

    expect(engine.spoken, isEmpty);
    expect(controller.warningKey, 'tts_playback_error');
  });
}
