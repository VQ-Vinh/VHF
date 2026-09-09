import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/core/localization.dart';
import 'package:prana_mobile/core/user_region.dart';
import 'package:prana_mobile/features/account/language_setting.dart';
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

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test(
    'country choices include English once and only bundled country locales',
    () {
      List<String> codes(String? country) =>
          CountryLocalePolicy.choices(
            country,
          ).map((l) => l.languageCode).toList();
      expect(codes('VN'), ['en', 'vi']);
      expect(codes('vn'), ['en', 'vi']);
      expect(codes('US'), ['en']);
      expect(codes('JP'), ['en']);
      expect(codes(null), ['en', 'vi']);
      expect(codes(''), ['en', 'vi']);
      expect(
        CountryLocalePolicy.reconcile(const Locale('en'), 'VN'),
        const Locale('en'),
      );
      expect(
        CountryLocalePolicy.reconcile(const Locale('vi'), 'VN'),
        const Locale('vi'),
      );
      expect(
        CountryLocalePolicy.reconcile(const Locale('vi'), 'JP'),
        const Locale('en'),
      );
    },
  );

  test('late storage read cannot replace a newer selection', () async {
    final storage = _DelayedStorage();
    final controller = AppLocaleController(storage);
    await controller.setLocale('en');
    storage.readResult.complete('vi');
    await controller.ready;
    expect(controller.locale, const Locale('en'));
    expect(storage.saved, 'en');
    controller.dispose();
  });

  test('country arriving before locale load reconciles and persists', () async {
    final storage = _DelayedStorage();
    final controller = AppLocaleController(storage);
    await controller.reconcileCountry('JP');
    storage.readResult.complete('vi');
    await controller.ready;
    expect(controller.locale, const Locale('en'));
    expect(storage.saved, 'en');
    await controller.reconcileCountry('VN');
    expect(controller.locale, const Locale('en'));
    await controller.setLocale('vi');
    await controller.reconcileCountry('VN');
    expect(controller.locale, const Locale('vi'));
    await controller.reconcileCountry('JP');
    expect(controller.locale, const Locale('en'));
    controller.dispose();
  });

  test('disposed controller ignores a late locale read', () async {
    final storage = _DelayedStorage();
    final controller = AppLocaleController(storage)..dispose();
    storage.readResult.complete('vi');
    await controller.ready;
    expect(controller.locale, isNull);
  });

  test('server Country wins over a late cached region', () async {
    final storage = _DelayedStorage();
    final region = UserRegionController(storage);
    await region.hydrate(country: 'VN', timezone: 'Asia/Ho_Chi_Minh');
    storage.readResult.complete('JP');
    await Future<void>.delayed(Duration.zero);
    expect(region.countryCode, 'VN');
    region.dispose();
  });

  test('bundled ARB messages and placeholder names match the template', () {
    final template =
        jsonDecode(File('lib/l10n/app_en.arb').readAsStringSync())
            as Map<String, dynamic>;
    final keys = template.keys.where((k) => !k.startsWith('@')).toSet();
    for (final locale in AppLocalizations.supportedLocales) {
      final arb =
          jsonDecode(
                File(
                  'lib/l10n/app_${locale.languageCode}.arb',
                ).readAsStringSync(),
              )
              as Map<String, dynamic>;
      expect(arb.keys.where((k) => !k.startsWith('@')).toSet(), keys);
      for (final key in keys) {
        Set<String?> placeholders(String text) =>
            RegExp(r'\{(\w+)\}').allMatches(text).map((m) => m[1]).toSet();
        expect(
          placeholders(arb[key] as String),
          placeholders(template[key] as String),
          reason: '$locale/$key',
        );
      }
    }
  });

  testWidgets('language setting aligns right and reflows without clipping', (
    tester,
  ) async {
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetDevicePixelRatio);
    addTearDown(tester.view.resetPhysicalSize);
    for (final width in [
      320.0,
      375.0,
      390.0,
      400.0,
      430.0,
      768.0,
      1024.0,
      1920.0,
    ]) {
      for (final scale in [1.0, 1.5, 2.0]) {
        for (final code in ['en', 'vi']) {
          tester.view.physicalSize = Size(width, 320);
          String? selected;
          await tester.pumpWidget(
            MaterialApp(
              locale: Locale(code),
              supportedLocales: AppLocalizations.supportedLocales,
              localizationsDelegates: AppLocalizations.localizationsDelegates,
              home: MediaQuery(
                data: MediaQueryData(textScaler: TextScaler.linear(scale)),
                child: Scaffold(
                  body: SingleChildScrollView(
                    child: Padding(
                      padding: const EdgeInsets.all(14),
                      child: LanguageSetting(
                        country: 'VN',
                        value: code,
                        onChanged: (v) => selected = v,
                      ),
                    ),
                  ),
                ),
              ),
            ),
          );
          await tester.pumpAndSettle();
          final toggle = tester.getRect(
            find.byKey(const ValueKey('interface-language-toggle')),
          );
          expect(toggle.right, closeTo(width - 14, .01));
          final en = find.byKey(const ValueKey('interface-language-en'));
          final vi = find.byKey(const ValueKey('interface-language-vi'));
          expect(
            tester.getRect(en).right,
            lessThanOrEqualTo(tester.getRect(vi).left),
          );
          for (final button in [en, vi]) {
            expect(tester.getSize(button).width, greaterThanOrEqualTo(48));
            expect(tester.getSize(button).height, greaterThanOrEqualTo(48));
          }
          await tester.tap(en);
          expect(selected, 'en');
          expect(tester.takeException(), isNull, reason: '$width/$scale/$code');
        }
      }
    }
  });

  testWidgets('unsupported country only offers English with an explanation', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        home: Scaffold(
          body: LanguageSetting(country: 'JP', value: 'en', onChanged: (_) {}),
        ),
      ),
    );
    expect(find.byKey(const ValueKey('interface-language-en')), findsOneWidget);
    expect(find.byKey(const ValueKey('interface-language-vi')), findsNothing);
    expect(
      find.text(
        'Only an English interface is currently available for this country.',
      ),
      findsOneWidget,
    );
  });
}
