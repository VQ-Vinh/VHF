import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/legacy.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:google_sign_in/google_sign_in.dart';

import 'package:prana_mobile/data/network/prana_api.dart';
import 'package:prana_mobile/data/auth/authentication_service.dart';
import 'package:prana_mobile/core/localization.dart';
import 'package:prana_mobile/core/theme_mode.dart';
import 'package:prana_mobile/core/user_region.dart';

final authProvider = Provider<FirebaseAuth>((ref) => FirebaseAuth.instance);

final authenticationServiceProvider = Provider<AuthenticationService>(
  (ref) => FirebaseAuthenticationService(
    ref.watch(authProvider),
    GoogleSignIn.instance,
  ),
);

final apiProvider = Provider<PranaApi>(
  (ref) => PranaApi(ref.watch(authProvider)),
);

final secureStorageProvider = Provider<FlutterSecureStorage>(
  (ref) => const FlutterSecureStorage(aOptions: AndroidOptions()),
);

final appLocaleProvider = ChangeNotifierProvider<AppLocaleController>((ref) {
  final controller = AppLocaleController(ref.watch(secureStorageProvider));
  ref.listen<String?>(
    userRegionProvider.select((region) => region.countryCode),
    (_, country) => controller.reconcileCountry(country),
    fireImmediately: true,
  );
  return controller;
});

final appThemeModeProvider = ChangeNotifierProvider<AppThemeModeController>(
  (ref) => AppThemeModeController(ref.watch(secureStorageProvider)),
);

final userRegionProvider = ChangeNotifierProvider<UserRegionController>(
  (ref) => UserRegionController(ref.watch(secureStorageProvider)),
);

final authStateProvider = StreamProvider<User?>((ref) {
  return ref.watch(authProvider).userChanges();
});
