import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/app/di/auth_providers.dart';
import 'package:prana_mobile/core/theme.dart';
import 'package:prana_mobile/core/theme_mode.dart';
import 'package:prana_mobile/features/account/theme_setting.dart';
import 'package:prana_mobile/l10n/app_localizations.dart';

class _DelayedStorage extends Fake implements FlutterSecureStorage {
  final readResult = Completer<String?>();
  String? saved;

  @override
  Future<String?> read({
    required String key,
    AppleOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    AppleOptions? mOptions,
    WindowsOptions? wOptions,
  }) => readResult.future;

  @override
  Future<void> write({
    required String key,
    required String? value,
    AppleOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    AppleOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    saved = value;
  }
}

class _StateMarker extends StatefulWidget {
  const _StateMarker(this.onCreated);
  final VoidCallback onCreated;
  @override
  State<_StateMarker> createState() => _StateMarkerState();
}

class _StateMarkerState extends State<_StateMarker> {
  final controller = TextEditingController(text: 'draft');
  @override
  void initState() {
    super.initState();
    widget.onCreated();
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) =>
      TextField(key: const ValueKey('state-marker'), controller: controller);
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('theme defaults light and persists explicit changes', () async {
    final storage = _DelayedStorage();
    final controller = AppThemeModeController(storage);
    expect(controller.themeMode, ThemeMode.light);
    storage.readResult.complete(null);
    await controller.ready;
    await controller.setDarkMode(true);
    expect(controller.themeMode, ThemeMode.dark);
    expect(storage.saved, 'true');
    controller.dispose();
  });

  test('stored dark mode is restored', () async {
    final storage = _DelayedStorage();
    final controller = AppThemeModeController(storage);
    storage.readResult.complete('true');
    await controller.ready;
    expect(controller.darkMode, isTrue);
    controller.dispose();
  });

  test('late storage read cannot replace a newer choice', () async {
    final storage = _DelayedStorage();
    final controller = AppThemeModeController(storage);
    await controller.setDarkMode(true);
    storage.readResult.complete('false');
    await controller.ready;
    expect(controller.darkMode, isTrue);
    expect(storage.saved, 'true');
    controller.dispose();
  });

  test('disposed controller ignores a late read', () async {
    final storage = _DelayedStorage();
    final controller = AppThemeModeController(storage)..dispose();
    storage.readResult.complete('true');
    await controller.ready;
    expect(controller.darkMode, isFalse);
  });

  testWidgets('theme switches immediately without recreating child state', (
    tester,
  ) async {
    FlutterSecureStorage.setMockInitialValues({});
    var stateCreations = 0;
    await tester.pumpWidget(
      ProviderScope(
        child: Consumer(
          builder:
              (context, ref, _) => MaterialApp(
                theme: PranaTheme.light(),
                darkTheme: PranaTheme.dark(),
                themeMode: ref.watch(appThemeModeProvider).themeMode,
                home: Scaffold(body: _StateMarker(() => stateCreations++)),
              ),
        ),
      ),
    );
    await tester.enterText(
      find.byKey(const ValueKey('state-marker')),
      'unsent draft',
    );
    final context = tester.element(find.byType(_StateMarker));
    final container = ProviderScope.containerOf(context);
    await container.read(appThemeModeProvider).setDarkMode(true);
    await tester.pumpAndSettle();
    expect(
      Theme.of(tester.element(find.byType(_StateMarker))).brightness,
      Brightness.dark,
    );
    expect(stateCreations, 1);
    expect(find.text('unsent draft'), findsOneWidget);
  });

  testWidgets(
    'setting remains usable across viewports, themes and text scales',
    (tester) async {
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetDevicePixelRatio);
      addTearDown(tester.view.resetPhysicalSize);
      for (final size in [
        const Size(320, 800),
        const Size(375, 800),
        const Size(390, 800),
        const Size(400, 800),
        const Size(430, 800),
        const Size(768, 1024),
        const Size(1024, 768),
        const Size(1920, 1080),
        const Size(800, 320),
      ]) {
        for (final locale in const [Locale('vi'), Locale('en')]) {
          for (final scale in [1.0, 1.5, 2.0]) {
            for (final dark in [false, true]) {
              tester.view.physicalSize = size;
              bool? changed;
              await tester.pumpWidget(
                MaterialApp(
                  theme: PranaTheme.light(),
                  darkTheme: PranaTheme.dark(),
                  themeMode: dark ? ThemeMode.dark : ThemeMode.light,
                  locale: locale,
                  supportedLocales: AppLocalizations.supportedLocales,
                  localizationsDelegates:
                      AppLocalizations.localizationsDelegates,
                  home: MediaQuery(
                    data: MediaQueryData(textScaler: TextScaler.linear(scale)),
                    child: Scaffold(
                      body: SingleChildScrollView(
                        child: ThemeSetting(
                          darkMode: dark,
                          onChanged: (value) => changed = value,
                        ),
                      ),
                    ),
                  ),
                ),
              );
              await tester.pumpAndSettle();
              final setting = find.byKey(const ValueKey('dark-mode-setting'));
              expect(
                tester.getRect(setting).right,
                lessThanOrEqualTo(size.width),
              );
              await tester.tap(setting);
              expect(changed, !dark);
              expect(
                tester.takeException(),
                isNull,
                reason: '$size/$locale/$scale/dark=$dark',
              );
            }
          }
        }
      }
    },
  );

  test('dark theme uses readable semantic surfaces', () {
    final scheme = PranaTheme.dark().colorScheme;
    double contrast(Color a, Color b) {
      final lighter = a.computeLuminance() > b.computeLuminance() ? a : b;
      final darker = identical(lighter, a) ? b : a;
      return (lighter.computeLuminance() + .05) /
          (darker.computeLuminance() + .05);
    }

    expect(
      contrast(scheme.onSurface, scheme.surface),
      greaterThanOrEqualTo(4.5),
    );
    expect(
      contrast(scheme.onPrimary, scheme.primary),
      greaterThanOrEqualTo(4.5),
    );
  });
}
