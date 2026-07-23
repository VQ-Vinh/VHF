import 'package:firebase_core/firebase_core.dart';

abstract final class AppConfig {
  static const flavor = String.fromEnvironment(
    'FLAVOR',
    defaultValue: 'staging',
  );
  static const apiUrl = String.fromEnvironment(
    'API_URL',
    defaultValue: 'http://10.0.2.2:8080',
  );
  static const firebaseGoogleWebClientId = String.fromEnvironment(
    'FIREBASE_GOOGLE_WEB_CLIENT_ID',
  );

  static FirebaseOptions get firebaseOptions => const FirebaseOptions(
    apiKey: String.fromEnvironment('FIREBASE_API_KEY'),
    appId: String.fromEnvironment('FIREBASE_APP_ID'),
    messagingSenderId: String.fromEnvironment('FIREBASE_MESSAGING_SENDER_ID'),
    projectId: String.fromEnvironment('FIREBASE_PROJECT_ID'),
    storageBucket: String.fromEnvironment('FIREBASE_STORAGE_BUCKET'),
  );
}
