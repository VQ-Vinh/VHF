import 'dart:collection';

import 'package:flutter/foundation.dart';
import 'package:flutter_tts/flutter_tts.dart';

import '../models/station.dart';

abstract interface class SpeechEngine {
  Future<String?> resolveLocale(String preferredLocale);
  Future<void> speak(String text, String locale);
  Future<void> stop();
}

class FlutterTtsSpeechEngine implements SpeechEngine {
  FlutterTtsSpeechEngine({FlutterTts? tts}) : _tts = tts ?? FlutterTts() {
    _ready = _configure();
  }

  final FlutterTts _tts;
  late final Future<void> _ready;
  final Map<String, String> _resolvedLocales = <String, String>{};

  Future<void> _configure() async {
    await _tts.awaitSpeakCompletion(true);
    await _tts.setSpeechRate(0.45);
    await _tts.setVolume(1);
    await _tts.setPitch(1);
  }

  @override
  Future<String?> resolveLocale(String preferredLocale) async {
    await _ready;
    final cached = _resolvedLocales[preferredLocale];
    if (cached != null) return cached;

    var resolved = await _findCompatibleLocale(preferredLocale);
    if (resolved == null && defaultTargetPlatform == TargetPlatform.android) {
      final engines =
          (await _tts.getEngines as List<dynamic>? ?? const [])
              .map((engine) => engine.toString())
              .toSet();
      const googleEngine = 'com.google.android.tts';
      final defaultEngine = (await _tts.getDefaultEngine)?.toString();
      if (engines.contains(googleEngine) && defaultEngine != googleEngine) {
        await _tts.setEngine(googleEngine);
        await _configure();
        resolved = await _findCompatibleLocale(preferredLocale);
      }
    }
    if (resolved != null) _resolvedLocales[preferredLocale] = resolved;
    return resolved;
  }

  Future<String?> _findCompatibleLocale(String preferredLocale) async {
    if (await _tts.isLanguageAvailable(preferredLocale) == true) {
      return preferredLocale;
    }

    final languageCode = _languageCode(preferredLocale);
    final languages =
        (await _tts.getLanguages as List<dynamic>? ?? const [])
            .map((locale) => locale.toString())
            .where((locale) => _languageCode(locale) == languageCode)
            .toList();
    languages.sort((left, right) {
      final leftExact =
          _normalizeLocale(left) == _normalizeLocale(preferredLocale);
      final rightExact =
          _normalizeLocale(right) == _normalizeLocale(preferredLocale);
      return rightExact.toString().compareTo(leftExact.toString());
    });
    for (final locale in languages) {
      if (await _tts.isLanguageAvailable(locale) == true) return locale;
    }
    return null;
  }

  @override
  Future<void> speak(String text, String locale) async {
    await _ready;
    await _tts.setLanguage(locale);
    await _tts.speak(text);
  }

  @override
  Future<void> stop() async {
    await _ready;
    await _tts.stop();
  }

  static String _normalizeLocale(String locale) =>
      locale.trim().replaceAll('_', '-').toLowerCase();

  static String _languageCode(String locale) =>
      _normalizeLocale(locale).split('-').first;
}

class TranslationSpeechController extends ChangeNotifier {
  TranslationSpeechController(this._engine);

  static const locales = <String, String>{
    'vi': 'vi-VN',
    'en': 'en-US',
    'zh': 'zh-CN',
    'ja': 'ja-JP',
    'ko': 'ko-KR',
  };

  final SpeechEngine _engine;
  final Queue<_SpeechItem> _queue = Queue<_SpeechItem>();
  final Set<String> _seenRequestIds = <String>{};

  String? _stationId;
  String? _sessionId;
  String _fallbackLanguage = 'en';
  String? speakingRequestId;
  String? warningKey;
  bool _foreground = true;
  bool _needsBaseline = true;
  bool _draining = false;
  bool _disposed = false;
  int _epoch = 0;

  void trackStation(String stationId, String sessionId) {
    if (_stationId != stationId) {
      _stationId = stationId;
      _sessionId = sessionId;
      _seenRequestIds.clear();
      _queue.clear();
      // An idle Station has no existing results to suppress. Its first future
      // session should therefore speak the first translation it publishes.
      _needsBaseline = sessionId.isNotEmpty;
      _epoch++;
      _stopEngine();
      return;
    }
    _sessionId = sessionId;
  }

  void ingest(
    Iterable<TranslationResult> results, {
    required String fallbackLanguage,
  }) {
    if (!_foreground || _stationId == null || _sessionId == null) return;
    _fallbackLanguage = fallbackLanguage;
    final ordered = results.toList()..sort(compareTranslationChronologically);
    if (_needsBaseline) {
      _seenRequestIds.addAll(ordered.map((result) => result.requestId));
      _needsBaseline = false;
      return;
    }
    for (final result in ordered) {
      if (!_seenRequestIds.add(result.requestId)) continue;
      if (!_canSpeak(result)) continue;
      _queue.add(
        _SpeechItem(
          result: result,
          language: result.targetLanguage ?? fallbackLanguage,
        ),
      );
    }
    _drain();
  }

  Future<void> speakNow(TranslationResult result) async {
    if (!_canSpeak(result)) return;
    _queue.clear();
    _epoch++;
    await _stopSafely();
    speakingRequestId = null;
    _queue.addFirst(
      _SpeechItem(
        result: result,
        language: result.targetLanguage ?? _fallbackLanguage,
      ),
    );
    _draining = false;
    notifyListeners();
    await _drain();
  }

  Future<void> stopCurrent() async {
    _queue.clear();
    _epoch++;
    speakingRequestId = null;
    _draining = false;
    await _stopSafely();
    notifyListeners();
  }

  Future<void> setForeground(bool foreground) async {
    if (_foreground == foreground) return;
    _foreground = foreground;
    if (!foreground) {
      _queue.clear();
      _epoch++;
      speakingRequestId = null;
      await _stopSafely();
      notifyListeners();
      return;
    }
    _needsBaseline = true;
  }

  Future<void> reset() async {
    _stationId = null;
    _sessionId = null;
    _fallbackLanguage = 'en';
    _seenRequestIds.clear();
    _queue.clear();
    _needsBaseline = true;
    _epoch++;
    speakingRequestId = null;
    warningKey = null;
    await _stopSafely(reportError: false);
    notifyListeners();
  }

  void clearWarning() {
    if (warningKey == null) return;
    warningKey = null;
    notifyListeners();
  }

  bool _canSpeak(TranslationResult result) =>
      result.translation.trim().isNotEmpty &&
      !(result.error?.trim().isNotEmpty ?? false);

  Future<void> _drain() async {
    if (_draining || !_foreground || _queue.isEmpty) return;
    _draining = true;
    final epoch = _epoch;
    try {
      while (_foreground && _queue.isNotEmpty && epoch == _epoch) {
        final item = _queue.removeFirst();
        final preferredLocale = locales[item.language];
        String? locale;
        try {
          locale =
              preferredLocale == null
                  ? null
                  : await _engine.resolveLocale(preferredLocale);
        } catch (_) {
          warningKey = 'tts_playback_error';
          notifyListeners();
          continue;
        }
        if (locale == null) {
          warningKey = 'tts_language_unavailable';
          notifyListeners();
          continue;
        }
        speakingRequestId = item.result.requestId;
        warningKey = null;
        notifyListeners();
        try {
          await _engine.speak(item.result.translation, locale);
        } catch (_) {
          if (epoch == _epoch) {
            warningKey = 'tts_playback_error';
            notifyListeners();
          }
        } finally {
          if (epoch == _epoch) {
            speakingRequestId = null;
            notifyListeners();
          }
        }
      }
    } finally {
      if (epoch == _epoch) _draining = false;
    }
  }

  Future<void> _stopSafely({bool reportError = true}) async {
    try {
      await _engine.stop();
    } catch (_) {
      if (reportError) warningKey = 'tts_playback_error';
    }
  }

  void _stopEngine() {
    _stopSafely(reportError: false);
    speakingRequestId = null;
    if (!_disposed) notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    _queue.clear();
    _stopSafely(reportError: false);
    super.dispose();
  }
}

class _SpeechItem {
  const _SpeechItem({required this.result, required this.language});

  final TranslationResult result;
  final String language;
}
