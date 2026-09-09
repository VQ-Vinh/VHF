import 'package:flutter/foundation.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:prana_mobile/domain/radio/speech_engine.dart';

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
