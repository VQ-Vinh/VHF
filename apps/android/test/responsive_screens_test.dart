import 'package:prana_mobile/l10n/app_localizations.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/app/di/auth_providers.dart';
import 'package:prana_mobile/app/di/station_providers.dart';
import 'package:prana_mobile/core/theme.dart';
import 'package:prana_mobile/data/network/prana_api.dart';
import 'package:prana_mobile/domain/station/station.dart';
import 'package:prana_mobile/features/account/account_screen.dart';
import 'package:prana_mobile/features/auth/sign_in_screen.dart';
import 'package:prana_mobile/features/auth/verify_email_screen.dart';
import 'package:prana_mobile/features/pairing/pairing_screen.dart';
import 'package:prana_mobile/features/station/list/station_list_screen.dart';
import 'package:prana_mobile/domain/radio/tx/tx_draft.dart';
import 'package:prana_mobile/features/station/radio/presentation/widgets/tx/tx_review_card.dart';

void _ignoreTranslation(String value) {}
void _ignoreCancel() {}

class _User extends Fake implements User {
  @override
  String get uid => 'synthetic-owner';
  @override
  String get email => 'synthetic.account.with.a.long.name@example.invalid';
  @override
  bool get emailVerified => false;
  @override
  List<UserInfo> get providerData => [];
}

class _Api extends Fake implements PranaApi {
  @override
  Future<Map<String, dynamic>> account() async => {
    'status': 'pending_payment',
    'plan_id': 'free',
    'country_code': 'VN',
    'timezone': 'Asia/Ho_Chi_Minh',
  };
  @override
  Future<List<Map<String, dynamic>>> plans() async => [
    {
      'id': 'free',
      'name': 'Synthetic plan with a long name',
      'audio_seconds_limit': 600,
    },
  ];
  @override
  Future<List<Map<String, dynamic>>> devices() async => [
    {
      'id': 'synthetic-device',
      'name': 'Synthetic device with a long name',
      'active': true,
    },
  ];
  @override
  Future<List<Map<String, dynamic>>> stations() async => [
    {
      'id': 'synthetic-station',
      'name': 'Synthetic station with a long name',
      'platform': 'linux',
      'station_code': 'STATION_1234567890',
      'active': true,
    },
  ];
}

void main() {
  for (final (name, screen) in <(String, Widget)>[
    ('sign-in', const SignInScreen()),
    ('verify', const VerifyEmailScreen()),
    ('pairing', PairingScreen(initialUri: Uri(path: '/pair'))),
    ('account', const AccountScreen()),
    ('stations', const StationListScreen()),
    (
      'review',
      const Scaffold(
        body: TxReviewCard(
          draft: TxDraft(
            id: 'draft',
            stationId: 's',
            duration: Duration(seconds: 120),
            targetLanguage: 'vi',
            transcript: 'A synthetic transcript with enough words to wrap.',
            translation:
                'A synthetic editable translation with enough words to wrap.',
          ),
          languageLabel: 'Vietnamese',
          onTransmit: _ignoreTranslation,
          onCancel: _ignoreCancel,
        ),
      ),
    ),
  ]) {
    testWidgets('$name reflows across widths, languages, text and keyboard', (
      tester,
    ) async {
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetDevicePixelRatio);
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetViewInsets);
      FlutterSecureStorage.setMockInitialValues({});
      for (final locale in ['vi', 'en']) {
        for (final scale in [1.0, 1.5, 2.0]) {
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
            tester.view.physicalSize = size;
            await tester.pumpWidget(
              ProviderScope(
                overrides: [
                  authStateProvider.overrideWith(
                    (ref) => Stream.value(_User()),
                  ),
                  apiProvider.overrideWithValue(_Api()),
                  stationsProvider.overrideWith(
                    (ref) => Stream.value([
                      StationModel(
                        id: 's',
                        name: 'Synthetic station with a long display name',
                        platform: 'linux',
                        active: true,
                        captureState: 'idle',
                        observedGeneration: 1,
                        sessionId: '',
                        sequence: 0,
                        lastSeenAt: DateTime.now(),
                        desired: const DesiredState(
                          running: false,
                          targetLanguage: 'vi',
                          retryGeneration: 0,
                          generation: 1,
                        ),
                      ),
                    ]),
                  ),
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
                  home: screen,
                ),
              ),
            );
            await tester.pump();
            await tester.pump(const Duration(milliseconds: 300));
            expect(
              tester.takeException(),
              isNull,
              reason: '$name/$size/$locale/$scale',
            );
            // Visit lazy content as well as the first viewport.
            final scrollables = find.byType(Scrollable);
            if (scrollables.evaluate().isNotEmpty) {
              final state = tester.state<ScrollableState>(scrollables.first);
              for (
                var i = 0;
                i < 20 &&
                    state.position.pixels < state.position.maxScrollExtent;
                i++
              ) {
                state.position.jumpTo(
                  (state.position.pixels + size.height / 2).clamp(
                    0,
                    state.position.maxScrollExtent,
                  ),
                );
                await tester.pump();
                expect(
                  tester.takeException(),
                  isNull,
                  reason: 'scrolled $name/$size/$locale/$scale',
                );
              }
            }
            tester.view.viewInsets = FakeViewPadding(bottom: size.height * .35);
            await tester.pump();
            expect(
              tester.takeException(),
              isNull,
              reason: 'keyboard $name/$size/$locale/$scale',
            );
            tester.view.resetViewInsets();
            await tester.pumpWidget(const SizedBox.shrink());
          }
        }
      }
    });
  }
}
