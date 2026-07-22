import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_sign_in/google_sign_in.dart';

import 'app.dart';
import 'core/app_config.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp(options: AppConfig.firebaseOptions);
  await GoogleSignIn.instance.initialize(
    serverClientId: AppConfig.firebaseGoogleWebClientId,
  );
  runApp(const ProviderScope(child: PranaMobileApp()));
}
