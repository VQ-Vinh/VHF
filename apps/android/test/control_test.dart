import 'package:prana_mobile/l10n/app_localizations.dart';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/app/di/telemetry_providers.dart';
import 'package:prana_mobile/core/theme.dart';
import 'package:prana_mobile/telemetry/data/mock_telemetry_generator.dart';
import 'package:prana_mobile/features/station/control/application/steering_state.dart';
import 'package:prana_mobile/features/station/control/presentation/control_tab.dart';
import 'package:prana_mobile/features/station/control/presentation/widgets/control_widget.dart';
import 'package:prana_mobile/features/station/control/presentation/widgets/coordinates.dart';
import 'package:prana_mobile/features/station/control/presentation/widgets/rudder_scale.dart';
import 'package:prana_mobile/features/station/control/presentation/widgets/steering_wheel.dart';
import 'telemetry_instruments_test.dart' show TestTelemetry;

void main() {
  test(
    'steering unwraps bearings, clamps and ends gestures without recentering',
    () {
      final state = SteeringState();
      state.beginDrag(179 * math.pi / 180);
      state.drag(-179 * math.pi / 180);
      expect(state.angle, closeTo(2, .001));
      state.drag(179 * math.pi / 180);
      expect(state.angle, closeTo(0, .001));
      state.adjust(300);
      expect(state.angle, 180);
      state.adjust(-600);
      expect(state.angle, -180);
      state.center();
      state.adjust(5);
      state.endDrag();
      state.drag(0);
      expect(state.angle, 5);
      state.selectMode(MockControlMode.auto);
      state.adjust(5);
      expect(state.angle, 0);
      state.selectMode(MockControlMode.manual);
      expect(state.angle, 0);
    },
  );

  test('the rudder scale clamps to the range the state can reach', () {
    expect(RudderScale.fraction(0), 0);
    expect(RudderScale.fraction(90), closeTo(0.5, 1e-9));
    expect(RudderScale.fraction(-180), -1);
    // SteeringState clamps at 180, but the bar must stay on the bar even if a
    // caller ever hands it more.
    expect(RudderScale.fraction(400), 1);
    expect(RudderScale.fraction(-400), -1);
  });

  test('a fix reads in degrees, minutes and seconds, never with a minus', () {
    expect(formatDms(10.769722, positive: 'N', negative: 'S'), '10°46\'11"N');
    expect(formatDms(106.661944, positive: 'E', negative: 'W'), '106°39\'43"E');
    // A southern or western fix takes the other letter, not a minus sign.
    expect(formatDms(-33.8688, positive: 'N', negative: 'S'), '33°52\'08"S');
    expect(formatDms(-151.2093, positive: 'E', negative: 'W'), '151°12\'33"W');
    // Rounding carries into minutes and degrees rather than printing 60.
    expect(formatDms(10.999999, positive: 'N', negative: 'S'), '11°00\'00"N');
    expect(formatDms(0, positive: 'N', negative: 'S'), '0°00\'00"N');
  });

  testWidgets('Control carries the readings the Dashboard tab used to', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(430, 932);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final repo = TestTelemetry();
    await tester.pumpWidget(
      ProviderScope(
        overrides: [telemetryRepositoryProvider.overrideWithValue(repo)],
        child: MaterialApp(
          theme: PranaTheme.light(),
          locale: const Locale('en'),
          supportedLocales: AppLocalizations.supportedLocales,
          localizationsDelegates: const [
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          home: const Scaffold(body: ControlTab(stationId: 's', active: true)),
        ),
      ),
    );
    await tester.pump();
    // Two samples, the pinned one last, so the speed carries a delta.
    final generator = MockTelemetryGenerator();
    repo.stream.add(generator.at(const Duration(seconds: 4), DateTime.now()));
    repo.stream.add(generator.at(Duration.zero, DateTime.now()));
    await tester.pump();
    await tester.pump();

    // The three readings, in the strip above the chart.
    expect(find.byKey(const ValueKey('control-instruments')), findsOneWidget);
    expect(find.text('10.2'), findsOneWidget);
    expect(find.text('KT'), findsOneWidget);
    expect(find.text('8.2'), findsOneWidget);
    expect(find.text('315'), findsOneWidget, reason: 'three-digit bearing');
    expect(find.text('NW'), findsOneWidget);
    // Nothing knows whether the heading is true or magnetic, so nothing says.
    expect(find.textContaining('TRUE'), findsNothing);
    for (final icon in const [
      Icons.speed,
      Icons.vertical_align_bottom,
      Icons.explore_outlined,
    ]) {
      expect(find.byIcon(icon), findsOneWidget);
    }

    // The fix, on the chart, in degrees and minutes and seconds.
    expect(find.byKey(const ValueKey('gps-coordinates')), findsOneWidget);
    expect(find.textContaining('"N'), findsOneWidget);
    expect(find.textContaining('"E'), findsOneWidget);
    expect(find.byKey(const ValueKey('telemetry-map')), findsOneWidget);

    // The source is what it really is, and no accuracy is claimed.
    expect(
      find.descendant(
        of: find.byKey(const ValueKey('gps-source')),
        matching: find.text('SIMULATED'),
      ),
      findsOneWidget,
    );
    expect(find.textContaining('HDOP'), findsNothing);
    expect(find.textContaining('NMEA'), findsNothing);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox.shrink());
    await repo.stream.close();
  });

  testWidgets('the mode selector reports the mode that was tapped', (
    tester,
  ) async {
    final tapped = <MockControlMode>[];
    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        theme: PranaTheme.light(),
        locale: const Locale('en'),
        home: Scaffold(
          body: ControlWidget(
            mode: MockControlMode.manual,
            onChanged: tapped.add,
          ),
        ),
      ),
    );
    await tester.tap(find.text('Auto'));
    await tester.tap(find.text('Manual'));
    expect(tapped, [MockControlMode.auto, MockControlMode.manual]);
    expect(tester.takeException(), isNull);
  });

  testWidgets('wheel drag and buttons retain angle, deactivate on tab leave', (
    tester,
  ) async {
    final state = SteeringState();
    Future<void> show(bool active) => tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        theme: PranaTheme.light(),
        home: Scaffold(
          body: StatefulBuilder(
            builder:
                (context, update) => SteeringWheel(
                  state: state,
                  active: active,
                  onChanged: () => update(() {}),
                ),
          ),
        ),
      ),
    );
    final semantics = tester.ensureSemantics();

    await show(true);
    await tester.tap(find.byKey(const ValueKey('steering-right')));
    expect(state.angle, 5);
    await tester.tap(find.byKey(const ValueKey('steering-center')));
    final box = tester.getRect(find.byKey(const ValueKey('steering-wheel')));
    final gesture = await tester.startGesture(
      box.center + const Offset(100, 0),
    );
    await gesture.moveBy(const Offset(0, 30));
    await gesture.moveBy(const Offset(-30, 40));
    expect(state.angle, greaterThan(0));
    final retained = state.angle;
    await show(false);
    await gesture.moveBy(const Offset(-30, 30));
    await gesture.up();
    expect(state.angle, retained);
    await show(true);
    expect(state.angle, retained);
    state.selectMode(MockControlMode.auto);
    await show(true);
    expect(
      tester
          .widget<IconButton>(find.byKey(const ValueKey('steering-right')))
          .onPressed,
      isNull,
    );
    expect(state.angle, 0);
    expect(tester.takeException(), isNull);
    semantics.dispose();
  });

  testWidgets(
    'Control reflows with fixed coordinates and one telemetry subscription',
    (tester) async {
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      for (final size in [
        const Size(320, 800),
        const Size(375, 800),
        const Size(390, 800),
        const Size(400, 800),
        const Size(430, 800),
        const Size(768, 1024),
        const Size(1024, 768),
        const Size(1440, 900),
        const Size(1920, 1080),
        const Size(800, 320),
      ]) {
        for (final locale in ['vi', 'en']) {
          for (final scale in [1.0, 1.5, 2.0]) {
            tester.view.physicalSize = size;
            final repo = TestTelemetry();
            await tester.pumpWidget(
              ProviderScope(
                overrides: [
                  telemetryRepositoryProvider.overrideWithValue(repo),
                ],
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
                    body: ControlTab(stationId: 's', active: true),
                  ),
                ),
              ),
            );
            await tester.pump();
            final strip = find.byKey(const ValueKey('control-instruments'));
            final pinned = strip.evaluate().isNotEmpty;
            final before = pinned ? tester.getRect(strip) : null;
            final scroll = tester.state<ScrollableState>(
              find.byType(Scrollable).first,
            );
            scroll.position.jumpTo(scroll.position.maxScrollExtent);
            await tester.pump();
            if (pinned) {
              // Speed, depth and heading stay put while the wheel is scrolled
              // to; stacked they are too tall to hold and scroll with the rest.
              expect(
                tester.getRect(strip),
                before,
                reason: '$size/$locale/$scale',
              );
            }
            expect(repo.watches, 1);
            expect(
              tester.takeException(),
              isNull,
              reason: '$size/$locale/$scale',
            );
            await tester.pumpWidget(const SizedBox.shrink());
            await repo.stream.close();
          }
        }
      }
    },
  );
}
