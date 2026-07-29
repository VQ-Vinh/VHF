import 'dart:collection';
import 'dart:io';
import 'dart:typed_data';

import 'package:just_audio/just_audio.dart';
import 'package:path_provider/path_provider.dart';

import 'prana_api.dart';

abstract interface class SourceAudioEngine {
  Future<void> play(String stationId, String sessionId, String requestId);
  Future<void> stop();
  Future<void> clearCache();
}

typedef SourceAudioLoader =
    Future<Uint8List> Function(
      String stationId,
      String sessionId,
      String requestId,
    );

abstract interface class SourceFilePlayer {
  Future<void> playFile(String path);
  Future<void> stop();
}

class JustAudioSourceFilePlayer implements SourceFilePlayer {
  JustAudioSourceFilePlayer({AudioPlayer? player})
    : _player = player ?? AudioPlayer();

  final AudioPlayer _player;

  @override
  Future<void> playFile(String path) async {
    await _player.setFilePath(path);
    await _player.play();
  }

  @override
  Future<void> stop() => _player.stop();
}

class CachedSourceAudioEngine implements SourceAudioEngine {
  CachedSourceAudioEngine(PranaApi api, {SourceFilePlayer? player})
    : this._(
        loader: api.stationResultAudio,
        player: player ?? JustAudioSourceFilePlayer(),
        temporaryDirectory: getTemporaryDirectory,
      );

  CachedSourceAudioEngine.forTesting({
    required SourceAudioLoader loader,
    required SourceFilePlayer player,
    required Future<Directory> Function() temporaryDirectory,
  }) : this._(
         loader: loader,
         player: player,
         temporaryDirectory: temporaryDirectory,
       );

  CachedSourceAudioEngine._({
    required SourceAudioLoader loader,
    required SourceFilePlayer player,
    required Future<Directory> Function() temporaryDirectory,
  }) : _loader = loader,
       _player = player,
       _temporaryDirectory = temporaryDirectory;

  static const maxCachedFiles = 10;

  final SourceAudioLoader _loader;
  final SourceFilePlayer _player;
  final Future<Directory> Function() _temporaryDirectory;
  final LinkedHashMap<String, File> _cache = LinkedHashMap<String, File>();

  @override
  Future<void> play(
    String stationId,
    String sessionId,
    String requestId,
  ) async {
    final key = '$stationId-$sessionId-$requestId';
    var file = _cache.remove(key);
    if (file == null || !await file.exists()) {
      final bytes = await _loader(stationId, sessionId, requestId);
      if (bytes.isEmpty) throw StateError('Source audio is empty');
      final directory = await _temporaryDirectory();
      final safeKey = key.replaceAll(RegExp(r'[^A-Za-z0-9_-]'), '_');
      file = File('${directory.path}/prana-source-$safeKey.wav');
      await file.writeAsBytes(bytes, flush: true);
    }
    _cache[key] = file;
    await _trimCache();
    await _player.playFile(file.path);
  }

  Future<void> _trimCache() async {
    while (_cache.length > maxCachedFiles) {
      final oldestKey = _cache.keys.first;
      final oldest = _cache.remove(oldestKey);
      if (oldest != null && await oldest.exists()) {
        await oldest.delete();
      }
    }
  }

  @override
  Future<void> stop() => _player.stop();

  @override
  Future<void> clearCache() async {
    await stop();
    final files = _cache.values.toList();
    _cache.clear();
    for (final file in files) {
      if (await file.exists()) await file.delete();
    }
  }
}
