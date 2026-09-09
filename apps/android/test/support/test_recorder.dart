import 'dart:async';
import 'package:prana_mobile/domain/radio/tx/tx_recorder.dart';

class TestRecorder implements TxRecorder {
  int starts = 0, stops = 0, cancels = 0, disposals = 0;
  Completer<void>? startGate;
  @override
  Future<void> start() async {
    starts++;
    await startGate?.future;
  }

  @override
  Future<String> stop() async {
    stops++;
    return 'test.wav';
  }

  @override
  Future<void> cancel() async {
    cancels++;
  }

  @override
  Future<void> dispose() async {
    disposals++;
  }
}
