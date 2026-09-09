import 'package:prana_mobile/domain/radio/source_audio_engine.dart';
import 'package:prana_mobile/domain/radio/results.dart';
import 'dart:collection';

import 'package:flutter/foundation.dart';
import 'package:prana_mobile/domain/radio/speech_engine.dart';

class TranslationSpeechController extends ChangeNotifier {
  TranslationSpeechController(this._engine, this._sourceAudio);

  static const locales = <String, String>{
    'vi': 'vi-VN',
    'en': 'en-US',
    'zh': 'zh-CN',
    'ja': 'ja-JP',
    'ko': 'ko-KR',
  };

  final SpeechEngine _engine;
  final SourceAudioEngine _sourceAudio;
  final Queue<_SpeechItem> _queue = Queue<_SpeechItem>();
  final Set<String> _seenRequestIds = <String>{};

  String? _stationId;
  String? _dayKey;
  String _fallbackSessionId = '';
  String _fallbackLanguage = 'en';
  String? speakingRequestId;
  String? warningKey;
  bool autoPlaybackEnabled = true;
  bool _foreground = true;
  bool _needsBaseline = true;
  bool _draining = false;
  bool _disposed = false;
  int _epoch = 0;
  Future<void> _sourceReady = Future<void>.value();

  void trackStation(
    String stationId,
    String dayKey, {
    String fallbackSessionId = '',
  }) {
    _fallbackSessionId = fallbackSessionId;
    if (_stationId != stationId || _dayKey != dayKey) {
      _stationId = stationId;
      _dayKey = dayKey;
      _seenRequestIds.clear();
      _queue.clear();
      _needsBaseline = true;
      _epoch++;
      _draining = false;
      _stopEngine();
      _sourceReady = _sourceReady
          .catchError((_) {})
          .then((_) => _sourceAudio.clearCache());
      return;
    }
  }

  void ingest(
    Iterable<TranslationResult> results, {
    required String fallbackLanguage,
  }) {
    if (!_foreground || _stationId == null || _dayKey == null) return;
    _fallbackLanguage = fallbackLanguage;
    final ordered = results.toList()..sort(compareTranslationChronologically);
    if (_needsBaseline) {
      _seenRequestIds.addAll(ordered.map((result) => result.requestId));
      _needsBaseline = false;
      return;
    }
    for (final result in ordered) {
      if (!_seenRequestIds.add(result.requestId)) continue;
      if (!autoPlaybackEnabled) continue;
      if (!_canSpeak(result)) continue;
      _queue.add(
        _SpeechItem(
          result: result,
          language: result.targetLanguage ?? fallbackLanguage,
          stationId: _stationId!,
          sessionId:
              result.sessionId.isNotEmpty
                  ? result.sessionId
                  : _fallbackSessionId,
        ),
      );
    }
    _drain();
  }

  Future<void> setAutoPlaybackEnabled(bool enabled) async {
    if (autoPlaybackEnabled == enabled) return;
    autoPlaybackEnabled = enabled;
    if (!enabled) {
      _queue.clear();
      _epoch++;
      speakingRequestId = null;
      _draining = false;
      await _stopSafely();
    }
    if (!_disposed) notifyListeners();
  }

  Future<void> speakNow(TranslationResult result) async {
    if (!_canSpeak(result)) return;
    _queue.clear();
    _epoch++;
    final epoch = _epoch;
    await _stopSafely();
    if (_disposed || epoch != _epoch || _stationId == null) return;
    speakingRequestId = null;
    _queue.addFirst(
      _SpeechItem(
        result: result,
        language: result.targetLanguage ?? _fallbackLanguage,
        stationId: _stationId!,
        sessionId:
            result.sessionId.isNotEmpty ? result.sessionId : _fallbackSessionId,
      ),
    );
    _draining = false;
    if (!_disposed) notifyListeners();
    await _drain();
  }

  Future<void> stopCurrent() async {
    _queue.clear();
    _epoch++;
    speakingRequestId = null;
    _draining = false;
    await _stopSafely();
    if (!_disposed) notifyListeners();
  }

  Future<void> setForeground(bool foreground) async {
    if (_foreground == foreground) return;
    _foreground = foreground;
    _draining = false;
    if (!foreground) {
      _queue.clear();
      _epoch++;
      speakingRequestId = null;
      await _stopSafely();
      if (!_disposed) notifyListeners();
      return;
    }
    _needsBaseline = true;
  }

  Future<void> reset() async {
    _draining = false;
    _stationId = null;
    _dayKey = null;
    _fallbackSessionId = '';
    _fallbackLanguage = 'en';
    _seenRequestIds.clear();
    _queue.clear();
    _needsBaseline = true;
    _epoch++;
    speakingRequestId = null;
    warningKey = null;
    await _stopSafely(reportError: false);
    await _sourceAudio.clearCache();
    if (!_disposed) notifyListeners();
  }

  void clearWarning() {
    if (warningKey == null) return;
    warningKey = null;
    if (!_disposed) notifyListeners();
  }

  bool _canSpeak(TranslationResult result) =>
      (result.translation.trim().isNotEmpty ||
          result.transcript.trim().isNotEmpty) &&
      !(result.error?.trim().isNotEmpty ?? false);

  static String _languageCode(String value) =>
      value.trim().replaceAll('_', '-').toLowerCase().split('-').first;

  Future<void> _drain() async {
    if (_draining || !_foreground || _queue.isEmpty) return;
    _draining = true;
    final epoch = _epoch;
    try {
      while (_foreground && _queue.isNotEmpty && epoch == _epoch) {
        final item = _queue.removeFirst();
        speakingRequestId = item.result.requestId;
        warningKey = null;
        if (!_disposed) notifyListeners();
        try {
          final detected = _languageCode(item.result.language);
          final target = _languageCode(item.language);
          if (detected.isNotEmpty && detected == target) {
            try {
              await _sourceReady;
              if (_disposed || epoch != _epoch || !_foreground) return;
              await _sourceAudio.play(
                item.stationId,
                item.sessionId,
                item.result.requestId,
              );
            } catch (_) {
              await _speakText(item.result.transcript, detected, epoch);
            }
          } else {
            await _speakText(item.result.translation, target, epoch);
          }
        } catch (_) {
          if (epoch == _epoch) {
            warningKey = 'tts_playback_error';
            if (!_disposed) notifyListeners();
          }
        } finally {
          if (epoch == _epoch) {
            speakingRequestId = null;
            if (!_disposed) notifyListeners();
          }
        }
      }
    } finally {
      if (epoch == _epoch) _draining = false;
    }
  }

  Future<void> _speakText(String text, String language, int epoch) async {
    if (_disposed || epoch != _epoch || !_foreground) return;
    if (text.trim().isEmpty) throw StateError('Speech text is empty');
    final preferredLocale = locales[language];
    final locale =
        preferredLocale == null
            ? null
            : await _engine.resolveLocale(preferredLocale);
    if (_disposed || epoch != _epoch || !_foreground) return;
    if (locale == null) {
      warningKey = 'tts_language_unavailable';
      if (!_disposed) notifyListeners();
      return;
    }
    await _engine.speak(text, locale);
  }

  Future<void> _stopSafely({bool reportError = true}) async {
    try {
      await _engine.stop();
    } catch (_) {
      if (reportError) warningKey = 'tts_playback_error';
    }
    try {
      await _sourceAudio.stop();
    } catch (_) {
      if (reportError) warningKey = 'tts_playback_error';
    }
  }

  void _stopEngine() {
    _stopSafely(reportError: false);
    _sourceAudio.clearCache();
    speakingRequestId = null;
    if (!_disposed) notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    _epoch++;
    _queue.clear();
    _stopSafely(reportError: false);
    super.dispose();
  }
}

class _SpeechItem {
  const _SpeechItem({
    required this.result,
    required this.language,
    required this.stationId,
    required this.sessionId,
  });

  final TranslationResult result;
  final String language;
  final String stationId;
  final String sessionId;
}
