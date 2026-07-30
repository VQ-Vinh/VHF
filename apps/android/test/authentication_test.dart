import 'dart:io';

import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:prana_mobile/features/auth/auth_validation.dart';
import 'package:prana_mobile/services/authentication_service.dart';

void main() {
  test('email validation rejects empty and malformed values', () {
    expect(isValidEmail(''), isFalse);
    expect(isValidEmail('person'), isFalse);
    expect(isValidEmail('person@example'), isFalse);
    expect(isValidEmail('person@example.com'), isTrue);
    expect(isValidEmail(' person@example.com '), isTrue);
  });

  test('sign-up password requires length, uppercase, letter, and number', () {
    expect(isValidPassword('12345'), isFalse);
    expect(isValidPassword('123456'), isFalse);
    expect(isValidPassword('abcdef'), isFalse);
    expect(isValidPassword('Abcdef'), isFalse);
    expect(isValidPassword('abc123'), isFalse);
    expect(isValidPassword('Abc123'), isTrue);
    expect(passwordsMatch('Abc123', ''), isFalse);
    expect(passwordsMatch('Abc123', 'Other1'), isFalse);
    expect(passwordsMatch('Abc123', 'Abc123'), isTrue);
  });

  test('Firebase errors map to stable localized keys', () {
    expect(
      authenticationErrorKey(FirebaseAuthException(code: 'invalid-credential')),
      'auth_invalid_credentials',
    );
    expect(
      authenticationErrorKey(FirebaseAuthException(code: 'user-not-found')),
      'auth_invalid_credentials',
    );
    expect(
      authenticationErrorKey(
        FirebaseAuthException(code: 'email-already-in-use'),
      ),
      'auth_email_in_use',
    );
    expect(
      authenticationErrorKey(
        FirebaseAuthException(
          code: 'unknown',
          message: 'dev.flutter.pigeon.internal',
        ),
      ),
      'auth_unknown_error',
    );
  });

  test('Google cancel is silent and other Google errors are friendly', () {
    expect(
      authenticationErrorKey(
        const GoogleSignInException(code: GoogleSignInExceptionCode.canceled),
      ),
      isEmpty,
    );
    expect(
      authenticationErrorKey(
        const GoogleSignInException(
          code: GoogleSignInExceptionCode.unknownError,
        ),
      ),
      'auth_google_error',
    );
  });

  test('auth UI has tabs, local validation, and verification route', () {
    final signIn =
        File('lib/features/auth/sign_in_screen.dart').readAsStringSync();
    final router = File('lib/router.dart').readAsStringSync();
    final account =
        File('lib/features/account/account_screen.dart').readAsStringSync();

    expect(signIn, contains('TabBar('));
    expect(signIn, contains('TextFormField('));
    expect(signIn, contains('confirm_password'));
    expect(signIn, contains('google_sign_up'));
    expect(signIn, isNot(contains('exception.message')));
    expect(router, contains("'/verify-email'"));
    expect(router, contains('emailVerified'));
    expect(account, contains('confirm_sign_out'));
    expect(account, contains('authenticationServiceProvider'));
  });
}
