import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_sign_in/google_sign_in.dart';

import 'package:prana_mobile/app/app.dart';
import 'package:prana_mobile/core/app_config.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  LicenseRegistry.addLicense(_bundledFontLicenses);
  await Firebase.initializeApp(options: AppConfig.firebaseOptions);
  await GoogleSignIn.instance.initialize(
    serverClientId: AppConfig.firebaseGoogleWebClientId,
  );
  runApp(const ProviderScope(child: PranaMobileApp()));
}

/// The Live console's bundled faces are OFL 1.1, which asks that the licence
/// ship with them; registered here so any licence page lists it too.
Stream<LicenseEntry> _bundledFontLicenses() async* {
  for (final (family, file) in const [
    ('Roboto Mono', 'RobotoMono-OFL.txt'),
    ('Archivo', 'Archivo-OFL.txt'),
  ]) {
    yield LicenseEntryWithLineBreaks([
      family,
    ], await rootBundle.loadString('assets/fonts/$file'));
  }
}
