import 'package:prana_mobile/l10n/app_localizations.dart';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/app/di/telemetry_providers.dart';
import 'package:prana_mobile/core/theme.dart';
import 'package:prana_mobile/features/station/control/application/steering_state.dart';
import 'package:prana_mobile/features/station/control/presentation/control_tab.dart';
import 'package:prana_mobile/features/station/control/presentation/widgets/control_widget.dart';
import 'package:prana_mobile/features/station/control/presentation/widgets/position_widget.dart';
import 'package:prana_mobile/features/station/control/presentation/widgets/rudder_scale.dart';
import 'package:prana_mobile/features/station/control/presentation/widgets/steering_wheel.dart';
import 'package:prana_mobile/telemetry/domain/telemetry_repository.dart';
import 'dashboard_test.dart' show TestTelemetry;

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

  testWidgets('position reads hemispheres off the sign, not a minus sign', (
    tester,
  ) async {
    Future<void> show(TelemetryPosition? position) => tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        theme: PranaTheme.light(),
        home: Scaffold(
          body: PositionWidget(
            position: position,
            timestamp: DateTime.utc(2026, 9, 10, 22, 52, 34),
            showSource: false,
          ),
        ),
      ),
    );

    await show(TelemetryPosition(10.76972, 106.66188));
    expect(find.text('10.76972°  N'), findsOneWidget);
    expect(find.text('106.66188°  E'), findsOneWidget);

    await show(TelemetryPosition(-33.86880, -151.20930));
    expect(find.text('33.86880°  S'), findsOneWidget);
    expect(find.text('151.20930°  W'), findsOneWidget);
    expect(find.textContaining('-'), findsNothing);

    await show(null);
    expect(find.text('—'), findsNWidgets(2));
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
            final position = tester.getRect(
              find.byKey(const ValueKey('control-position')),
            );
            final scroll = tester.state<ScrollableState>(
              find.byType(Scrollable).first,
            );
            scroll.position.jumpTo(scroll.position.maxScrollExtent);
            await tester.pump();
            expect(
              tester.getRect(find.byKey(const ValueKey('control-position'))),
              position,
            );
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
