import 'package:prana_mobile/l10n/app_localizations.dart';
import 'package:prana_mobile/telemetry/data/mock_telemetry_repository.dart';
import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/app/di/telemetry_providers.dart';
import 'package:prana_mobile/core/theme.dart';
import 'package:prana_mobile/telemetry/domain/telemetry_repository.dart';
import 'package:prana_mobile/telemetry/data/mock_telemetry_generator.dart';
import 'package:prana_mobile/features/station/shared/application/station_telemetry_controller.dart';
import 'package:prana_mobile/features/station/dashboard/presentation/dashboard_tab.dart';
import 'package:prana_mobile/features/station/control/presentation/widgets/map_widget.dart';
import 'package:prana_mobile/features/station/dashboard/presentation/widgets/depth_scale.dart';
import 'package:prana_mobile/features/station/dashboard/presentation/widgets/speed_trend.dart';
import 'package:prana_mobile/features/station/dashboard/presentation/widgets/telemetry_delta.dart';

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
  for (final size in [
    const Size(320, 568),
    const Size(360, 800),
    const Size(375, 812),
    const Size(390, 844),
    const Size(400, 800),
    const Size(430, 932),
    const Size(800, 360),
    const Size(1024, 768),
    const Size(1280, 800),
  ]) {
    for (final scale in [1.0, 1.5, 2.0]) {
      for (final locale in ['vi', 'en']) {
        testWidgets('dashboard $size scale $scale locale $locale', (
          tester,
        ) async {
          tester.view.physicalSize = size;
          tester.view.devicePixelRatio = 1;
          addTearDown(tester.view.resetPhysicalSize);
          addTearDown(tester.view.resetDevicePixelRatio);
          final repo = TestTelemetry();
          await tester.pumpWidget(
            ProviderScope(
              overrides: [telemetryRepositoryProvider.overrideWithValue(repo)],
              child: MaterialApp(
                theme: PranaTheme.light(),
                locale: Locale(locale),
                supportedLocales: AppLocalizations.supportedLocales,
                localizationsDelegates: const [
                  AppLocalizations.delegate,
                  GlobalMaterialLocalizations.delegate,
                  GlobalWidgetsLocalizations.delegate,
                  GlobalCupertinoLocalizations.delegate,
                ],
                builder:
                    (context, child) => MediaQuery(
                      data: MediaQuery.of(
                        context,
                      ).copyWith(textScaler: TextScaler.linear(scale)),
                      child: child!,
                    ),
                home: const Scaffold(
                  body: DashboardTab(stationId: 'station', stationOnline: true),
                ),
              ),
            ),
          );
          await tester.pump();
          // Two samples, the pinned one last: the reading stays 10.2 while the
          // controller gains a previous sample and a history, so the delta chip
          // and the speed trend are both on screen. That is the densest the
          // card ever gets, which is what these widths need to prove.
          final generator = MockTelemetryGenerator();
          repo.stream.add(
            generator.at(const Duration(seconds: 4), DateTime.now()),
          );
          repo.stream.add(generator.at(Duration.zero, DateTime.now()));
          await tester.pump();
          await tester.pump();
          await tester.pump();
          for (final icon in [
            Icons.speed,
            Icons.vertical_align_bottom,
            Icons.explore_outlined,
          ]) {
            expect(find.byIcon(icon), findsOneWidget);
          }
          expect(find.text('10.2'), findsOneWidget);
          expect(find.text('°  NW'), findsOneWidget);
          expect(
            find.text(locale == 'vi' ? 'Tốc độ' : 'Speed'),
            findsOneWidget,
          );
          expect(
            find.text(locale == 'vi' ? 'Độ sâu' : 'Depth'),
            findsOneWidget,
          );
          expect(find.byKey(const ValueKey('compass-rose')), findsOneWidget);
          expect(find.byType(DepthScale), findsOneWidget);
          expect(find.byType(SpeedTrend), findsOneWidget);
          expect(find.byKey(const ValueKey('telemetry-map')), findsNothing);
          expect(tester.takeException(), isNull);
          await tester.pumpWidget(const SizedBox.shrink());
          await repo.stream.close();
        });
      }
    }
  }

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
          'lib/features/station/dashboard',
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
