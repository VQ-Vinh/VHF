abstract interface class SpeechEngine {
  Future<String?> resolveLocale(String preferredLocale);
  Future<void> speak(String text, String locale);
  Future<void> stop();
}
