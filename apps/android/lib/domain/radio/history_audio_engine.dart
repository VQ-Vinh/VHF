/// One manual TX History player. play completes on completion or stop.
/// Implementations own download/file cleanup and invalidate late completions.
abstract interface class HistoryAudioEngine {
  Future<void> play(String stationId, String jobId);
  Future<void> stop();
  Future<void> dispose();
}
