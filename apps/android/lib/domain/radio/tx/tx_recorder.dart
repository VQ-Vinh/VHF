abstract interface class TxRecorder {
  Future<void> start();
  Future<String> stop();
  Future<void> cancel();
  Future<void> dispose();
}
