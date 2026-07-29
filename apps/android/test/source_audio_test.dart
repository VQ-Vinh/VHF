import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/services/source_audio.dart';

class FakeFilePlayer implements SourceFilePlayer {
  final List<String> paths = [];
  int stopCalls = 0;

  @override
  Future<void> playFile(String path) async {
    paths.add(path);
  }

  @override
  Future<void> stop() async {
    stopCalls++;
  }
}

void main() {
  late Directory directory;

  setUp(() async {
    directory = await Directory.systemTemp.createTemp('prana-source-test-');
  });

  tearDown(() async {
    if (await directory.exists()) {
      await directory.delete(recursive: true);
    }
  });

  test('cache hit does not download source audio twice', () async {
    var downloads = 0;
    final player = FakeFilePlayer();
    final engine = CachedSourceAudioEngine.forTesting(
      loader: (_, _, _) async {
        downloads++;
        return Uint8List.fromList([1, 2, 3]);
      },
      player: player,
      temporaryDirectory: () async => directory,
    );

    await engine.play('station', 'session', 'request');
    await engine.play('station', 'session', 'request');

    expect(downloads, 1);
    expect(player.paths, hasLength(2));
    expect(player.paths.first, player.paths.last);
  });

  test('cache keeps only the ten most recent source files', () async {
    final player = FakeFilePlayer();
    final engine = CachedSourceAudioEngine.forTesting(
      loader:
          (_, _, requestId) async => Uint8List.fromList(requestId.codeUnits),
      player: player,
      temporaryDirectory: () async => directory,
    );

    for (var index = 0; index < 11; index++) {
      await engine.play('station', 'session', 'request-$index');
    }

    final files =
        directory
            .listSync()
            .whereType<File>()
            .map((file) => file.path)
            .toList();
    expect(files, hasLength(10));
    expect(files.any((path) => path.contains('request-0')), isFalse);
    expect(files.any((path) => path.contains('request-10')), isTrue);
  });

  test('clearCache stops playback and removes cached files', () async {
    final player = FakeFilePlayer();
    final engine = CachedSourceAudioEngine.forTesting(
      loader: (_, _, _) async => Uint8List.fromList([1]),
      player: player,
      temporaryDirectory: () async => directory,
    );
    await engine.play('station', 'session', 'request');

    await engine.clearCache();

    expect(player.stopCalls, 1);
    expect(directory.listSync(), isEmpty);
  });
}
