import 'package:prana_mobile/telemetry/data/mock_telemetry_repository.dart';
import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/core/theme.dart';
import 'package:prana_mobile/telemetry/domain/telemetry_repository.dart';
import 'package:prana_mobile/telemetry/data/mock_telemetry_generator.dart';
import 'package:prana_mobile/features/station/shared/application/station_telemetry_controller.dart';
import 'package:prana_mobile/features/station/control/presentation/widgets/map_widget.dart';
import 'package:prana_mobile/features/station/control/presentation/widgets/instruments/depth_scale.dart';
import 'package:prana_mobile/features/station/control/presentation/widgets/instruments/telemetry_delta.dart';

class TestTelemetry implements TelemetryRepository {
  final stream = StreamController<TelemetrySnapshot>.broadcast();
  int watches = 0;
  @override
  Stream<TelemetrySnapshot> watch(String stationId) {
    watches++;
    return stream.stream;
  }
}

void main() {
  test(
    'mock emits initial snapshot and injected ticks without network',
    () async {
      final now = DateTime.utc(2026, 9, 8);
      final repo = MockTelemetryRepository(
        clock: () => now,
        ticks:
            () => Stream.fromIterable([
              now.add(const Duration(seconds: 1)),
              now.add(const Duration(seconds: 2)),
            ]),
      );
      final samples = await repo.watch('s').toList();
      expect(samples.length, 3);
      expect(samples.first.timestamp, now);
      expect(samples.last.source, TelemetrySource.mock);
      expect(samples.last.headingDegrees, isNot(samples.first.headingDegrees));
    },
  );
  test('generator is deterministic and moves the coordinate marker', () {
    final generator = MockTelemetryGenerator();
    final now = DateTime.utc(2026, 9, 8);
    final first = generator.at(Duration.zero, now);
    final next = generator.at(
      const Duration(seconds: 4),
      now.add(const Duration(seconds: 4)),
    );
    expect(first.speedKnots, 10.2);
    expect(next.position.longitude, greaterThan(first.position.longitude));
    expect(
      TelemetryMapPainter(
        first.position,
        first.headingDegrees,
      ).markerOffset(const Size(400, 280)),
      isNot(
        TelemetryMapPainter(
          next.position,
          next.headingDegrees,
        ).markerOffset(const Size(400, 280)),
      ),
    );
  });

  test('freshness, retry and cancellation belong to the controller', () async {
    var now = DateTime.utc(2026, 9, 8);
    final repository = TestTelemetry();
    final controller = StationTelemetryController(
      repository,
      'station',
      clock: () => now,
    );
    await Future<void>.delayed(Duration.zero);
    expect(controller.state.freshness, TelemetryFreshness.missing);
    repository.stream.add(MockTelemetryGenerator().at(Duration.zero, now));
    await Future<void>.delayed(Duration.zero);
    expect(controller.state.freshness, TelemetryFreshness.fresh);
    now = now.add(const Duration(seconds: 6));
    controller.refreshFreshness();
    expect(controller.state.freshness, TelemetryFreshness.stale);
    repository.stream.addError(StateError('offline'));
    await Future<void>.delayed(Duration.zero);
    expect(controller.state.freshness, TelemetryFreshness.error);
    final retry = controller.retry();
    await Future<void>.delayed(Duration.zero);
    await retry;
    expect(repository.watches, 2);
    controller.dispose();
    expect(repository.stream.hasListener, false);
    await repository.stream.close();
  });

  // The handset widths AGENTS.md pins, plus the landscape and tablet cases.
  // 320 at text scale 2.0 is the tightest column the three instrument
  // graphics ever get.
  test('depth scale places decades evenly and clamps beyond the range', () {
    expect(DepthScale.fraction(1), 0);
    expect(DepthScale.fraction(10000), 1);
    // Each decade takes a quarter of the track, which is the whole point of
    // the log axis: an 8 m coastal reading stays visible on a 10 km range.
    expect(DepthScale.fraction(100), closeTo(0.5, 1e-9));
    expect(DepthScale.fraction(8), greaterThan(0.2));
    expect(DepthScale.fraction(0.2), 0);
    expect(DepthScale.fraction(99999), 1);
  });

  testWidgets(
    'delta chip shows direction, and nothing when it rounds to zero',
    (tester) async {
      Future<void> pumpDelta(double value) => tester.pumpWidget(
        MaterialApp(
          theme: PranaTheme.light(),
          home: Scaffold(body: TelemetryDelta(value: value, unit: 'kt')),
        ),
      );

      await pumpDelta(-0.4);
      expect(find.text('0.4 kt'), findsOneWidget);
      expect(find.byIcon(Icons.arrow_downward), findsOneWidget);

      await pumpDelta(0.4);
      expect(find.byIcon(Icons.arrow_upward), findsOneWidget);

      // 0.04 kt rounds to "0.0" at this precision; an arrow beside it would
      // claim a direction the number does not support.
      await pumpDelta(0.04);
      expect(find.byIcon(Icons.arrow_upward), findsNothing);
      expect(find.byIcon(Icons.arrow_downward), findsNothing);
      expect(find.text('0.0 kt'), findsNothing);
    },
  );

  test('dependency boundaries exclude UI-owned runtime and mock leaks', () {
    final runtime = Directory('lib/runtime')
        .listSync(recursive: true)
        .whereType<File>()
        .where((f) => f.path.endsWith('.dart'));
    for (final file in runtime) {
      expect(
        file.readAsStringSync(),
        isNot(contains('package:prana_mobile/features/')),
        reason: file.path,
      );
    }
    for (final file
        in Directory(
          'lib/features/station/control',
        ).listSync(recursive: true).whereType<File>()) {
      expect(
        file.readAsStringSync(),
        isNot(contains('telemetry/data/')),
        reason: file.path,
      );
      expect(
        file.readAsStringSync(),
        isNot(contains('radio/presentation')),
        reason: file.path,
      );
    }
    for (final file
        in Directory(
          'lib/domain',
        ).listSync(recursive: true).whereType<File>()) {
      expect(
        file.readAsStringSync(),
        isNot(contains('package:cloud_firestore')),
        reason: file.path,
      );
    }
    expect(File('lib/app/di/providers.dart').existsSync(), false);
    expect(
      Directory('lib/features/live').existsSync()
          ? Directory('lib/features/live').listSync().whereType<File>()
          : <File>[],
      isEmpty,
    );
  });
}
