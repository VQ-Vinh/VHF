import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';

abstract interface class TxRecorder {
  Future<void> start();
  Future<String> stop();
  Future<void> cancel();
  Future<void> dispose();
}

class PhoneTxRecorder implements TxRecorder {
  final AudioRecorder _recorder = AudioRecorder();
  String? _path;

  @override
  Future<void> start() async {
    if (!await _recorder.hasPermission()) {
      throw StateError('MICROPHONE_PERMISSION_DENIED');
    }
    final directory = await getTemporaryDirectory();
    _path = '${directory.path}/tx_${DateTime.now().microsecondsSinceEpoch}.wav';
    await _recorder.start(
      const RecordConfig(
        encoder: AudioEncoder.wav,
        sampleRate: 16000,
        numChannels: 1,
      ),
      path: _path!,
    );
  }

  @override
  Future<String> stop() async => await _recorder.stop() ?? (_path ?? '');

  @override
  Future<void> cancel() async {
    await _recorder.stop();
  }

  @override
  Future<void> dispose() => _recorder.dispose();
}
