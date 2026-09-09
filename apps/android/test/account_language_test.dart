import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/app/di/auth_providers.dart';
import 'package:prana_mobile/data/network/prana_api.dart';
import 'package:prana_mobile/features/account/account_screen.dart';
import 'package:prana_mobile/l10n/app_localizations.dart';

class _RegionApi extends Fake implements PranaApi {
  _RegionApi(this.fail);
  final bool fail;
  String country = 'VN';
  int updates = 0;
  @override
  Future<Map<String, dynamic>> account() async => {
    'country_code': country,
    'timezone': country == 'VN' ? 'Asia/Ho_Chi_Minh' : 'Asia/Tokyo',
  };
  @override
  Future<List<Map<String, dynamic>>> plans() async => [];
  @override
  Future<List<Map<String, dynamic>>> devices() async => [];
  @override
  Future<List<Map<String, dynamic>>> stations() async => [];
  @override
  Future<List<Map<String, dynamic>>> countries() async => [
    {
      'code': 'JP',
      'name': 'Japan',
      'timezones': ['Asia/Tokyo'],
    },
  ];
  @override
  Future<Map<String, dynamic>> updateRegion({
    required String countryCode,
    String? timezone,
  }) async {
    updates++;
    if (fail) throw const PranaApiFailure('error_request_failed');
    country = countryCode;
    return account();
  }
}

void main() {
  for (final fail in [false, true]) {
    testWidgets('country save reconciles locale only on success: fail=$fail', (
      tester,
    ) async {
      FlutterSecureStorage.setMockInitialValues({'app_locale': 'vi'});
      final api = _RegionApi(fail);
      final container = ProviderContainer(
        overrides: [
          apiProvider.overrideWithValue(api),
          authStateProvider.overrideWith((ref) => Stream.value(null)),
        ],
      );
      addTearDown(container.dispose);
      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: Consumer(
            builder:
                (context, ref, _) => MaterialApp(
                  locale: ref.watch(appLocaleProvider).locale,
                  supportedLocales: AppLocalizations.supportedLocales,
                  localizationsDelegates:
                      AppLocalizations.localizationsDelegates,
                  home: const AccountScreen(),
                ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(container.read(appLocaleProvider).locale, const Locale('vi'));
      final country = find.text('Quốc gia');
      await tester.ensureVisible(country);
      await tester.pumpAndSettle();
      await tester.tap(country);
      await tester.pumpAndSettle();
      await tester.tap(find.text('Japan'));
      await tester.pumpAndSettle();
      expect(api.updates, 1);
      expect(
        container.read(userRegionProvider).countryCode,
        fail ? 'VN' : 'JP',
      );
      expect(
        container.read(appLocaleProvider).locale,
        Locale(fail ? 'vi' : 'en'),
      );
      expect(
        find.byKey(const ValueKey('interface-language-vi')),
        fail ? findsOneWidget : findsNothing,
      );
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox.shrink());
    });
  }
}
