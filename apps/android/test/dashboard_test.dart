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

  for (final size in [
    const Size(360, 800),
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
          repo.stream.add(
            MockTelemetryGenerator().at(Duration.zero, DateTime.now()),
          );
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
          expect(find.byKey(const ValueKey('telemetry-map')), findsNothing);
          expect(tester.takeException(), isNull);
          await tester.pumpWidget(const SizedBox.shrink());
          await repo.stream.close();
        });
      }
    }
  }

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
