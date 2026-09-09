import 'package:prana_mobile/domain/radio/source_audio_engine.dart';
import 'dart:collection';
import 'dart:io';
import 'dart:typed_data';

import 'package:just_audio/just_audio.dart';
import 'package:path_provider/path_provider.dart';

import 'package:prana_mobile/data/network/prana_api.dart';

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

abstract interface class SourceFilePlayerLifecycle {
  Future<void> dispose();
}

class JustAudioSourceFilePlayer
    implements SourceFilePlayer, SourceFilePlayerLifecycle {
  JustAudioSourceFilePlayer({AudioPlayer? player})
    : _player = player ?? AudioPlayer();

  final AudioPlayer _player;
  int _epoch = 0;

  @override
  Future<void> playFile(String path) async {
    final epoch = ++_epoch;
    await _player.setFilePath(path);
    if (epoch != _epoch) return;
    await _player.play();
  }

  @override
  Future<void> stop() {
    _epoch++;
    return _player.stop();
  }

  @override
  Future<void> dispose() {
    _epoch++;
    return _player.dispose();
  }
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
  int _epoch = 0;

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
    final epoch = _epoch;
    final key = '$stationId-$sessionId-$requestId';
    var file = _cache.remove(key);
    if (file == null || !await file.exists()) {
      final bytes = await _loader(stationId, sessionId, requestId);
      if (epoch != _epoch) return;
      if (bytes.isEmpty) throw StateError('Source audio is empty');
      final directory = await _temporaryDirectory();
      if (epoch != _epoch) return;
      final safeKey = key.replaceAll(RegExp(r'[^A-Za-z0-9_-]'), '_');
      file = File('${directory.path}/prana-source-$safeKey.wav');
      await file.writeAsBytes(bytes, flush: true);
    }
    if (epoch != _epoch) {
      if (await file.exists()) await file.delete();
      return;
    }
    _cache[key] = file;
    await _trimCache();
    if (epoch != _epoch) return;
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
  Future<void> stop() {
    _epoch++;
    return _player.stop();
  }

  Future<void> dispose() async {
    await clearCache();
    final player = _player;
    if (player is SourceFilePlayerLifecycle) {
      await (player as SourceFilePlayerLifecycle).dispose();
    }
  }

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
