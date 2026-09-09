abstract interface class SourceAudioEngine {
  Future<void> play(String stationId, String sessionId, String requestId);
  Future<void> stop();
  Future<void> clearCache();
}
