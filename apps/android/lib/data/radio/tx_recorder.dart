import 'dart:io';
import 'package:prana_mobile/domain/radio/tx/tx_recorder.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';

class PhoneTxRecorder implements TxRecorder {
  final AudioRecorder _recorder = AudioRecorder();
  String? _path;
  Future<void>? _starting;
  bool _closed = false;

  @override
  Future<void> start() => _starting = _start();

  Future<void> _start() async {
    if (_closed) return;
    if (!await _recorder.hasPermission()) {
      throw StateError('MICROPHONE_PERMISSION_DENIED');
    }
    final directory = await getTemporaryDirectory();
    _path = '${directory.path}/tx_${DateTime.now().microsecondsSinceEpoch}.wav';
    if (_closed) return;
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
    if (_closed) return;
    try {
      await _starting;
    } catch (_) {}
    if (_closed) return;
    await _recorder.stop();
    await _removeFile();
  }

  Future<void> _removeFile() async {
    final path = _path;
    _path = null;
    if (path != null) {
      final file = File(path);
      if (await file.exists()) await file.delete();
    }
  }

  @override
  Future<void> dispose() async {
    _closed = true;
    try {
      await _starting;
    } catch (_) {}
    await _recorder.dispose();
    await _removeFile();
  }
}
