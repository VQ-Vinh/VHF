import 'dart:io';
import 'package:just_audio/just_audio.dart';
import 'package:path_provider/path_provider.dart';
import 'package:prana_mobile/data/network/prana_api.dart';
import 'package:prana_mobile/domain/radio/history_audio_engine.dart';

class NativeHistoryAudioEngine implements HistoryAudioEngine {
  NativeHistoryAudioEngine(this._api);
  final PranaApi _api;
  final _player = AudioPlayer();
  int _epoch = 0;
  bool _disposed = false;

  @override
  Future<void> play(String stationId, String jobId) async {
    final epoch = ++_epoch;
    bool current() => !_disposed && epoch == _epoch;
    File? file;
    try {
      await _player.stop();
      if (!current()) return;
      final bytes = await _api.txHistoryAudio(stationId, jobId);
      if (!current()) return;
      final directory = await getTemporaryDirectory();
      if (!current()) return;
      file = File(
        '${directory.path}/prana-tx-history-${identityHashCode(this)}-$epoch.wav',
      );
      await file.writeAsBytes(bytes, flush: true);
      if (!current()) return;
      await _player.setFilePath(file.path);
      if (!current()) return;
      await _player.play();
    } finally {
      if (file != null && await file.exists()) await file.delete();
    }
  }

  @override
  Future<void> stop() async {
    _epoch++;
    if (!_disposed) await _player.stop();
  }

  @override
  Future<void> dispose() async {
    _epoch++;
    _disposed = true;
    await _player.dispose();
  }
}
