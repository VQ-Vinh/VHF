import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart';
import 'package:google_sign_in/google_sign_in.dart';

abstract interface class AuthenticationService {
  Future<void> signIn({required String email, required String password});
  Future<void> signUp({required String email, required String password});
  Future<bool> signInWithGoogle();
  Future<void> sendPasswordReset(String email);
  Future<void> resendEmailVerification();
  Future<bool> refreshEmailVerification();
  Future<void> signOut();
}

class FirebaseAuthenticationService implements AuthenticationService {
  FirebaseAuthenticationService(this._auth, this._google);

  final FirebaseAuth _auth;
  final GoogleSignIn _google;

  @override
  Future<void> signIn({required String email, required String password}) async {
    await _auth.signInWithEmailAndPassword(email: email, password: password);
  }

  @override
  Future<void> signUp({required String email, required String password}) async {
    final credential = await _auth.createUserWithEmailAndPassword(
      email: email,
      password: password,
    );
    await credential.user?.sendEmailVerification();
  }

  @override
  Future<bool> signInWithGoogle() async {
    try {
      final googleUser = await _google.authenticate();
      final googleAuth = googleUser.authentication;
      await _auth.signInWithCredential(
        GoogleAuthProvider.credential(idToken: googleAuth.idToken),
      );
      return true;
    } on GoogleSignInException catch (exception) {
      if (exception.code == GoogleSignInExceptionCode.canceled) return false;
      rethrow;
    }
  }

  @override
  Future<void> sendPasswordReset(String email) =>
      _auth.sendPasswordResetEmail(email: email);

  @override
  Future<void> resendEmailVerification() async {
    final user = _auth.currentUser;
    if (user == null) throw StateError('No authenticated user');
    await user.sendEmailVerification();
  }

  @override
  Future<bool> refreshEmailVerification() async {
    final user = _auth.currentUser;
    if (user == null) return false;
    await user.reload();
    final refreshed = _auth.currentUser;
    if (refreshed?.emailVerified == true) {
      await refreshed?.getIdToken(true);
      return true;
    }
    return false;
  }

  @override
  Future<void> signOut() async {
    final usesGoogle =
        _auth.currentUser?.providerData.any(
          (provider) => provider.providerId == GoogleAuthProvider.PROVIDER_ID,
        ) ??
        false;
    if (usesGoogle) {
      try {
        await _google.signOut();
      } catch (error) {
        debugPrint('Google sign-out cleanup failed: $error');
      }
    }
    await _auth.signOut();
  }
}

String authenticationErrorKey(Object error) {
  if (error is FirebaseAuthException) {
    return switch (error.code) {
      'invalid-email' => 'auth_invalid_email',
      'invalid-credential' ||
      'wrong-password' ||
      'user-not-found' => 'auth_invalid_credentials',
      'email-already-in-use' => 'auth_email_in_use',
      'weak-password' => 'auth_weak_password',
      'user-disabled' => 'auth_user_disabled',
      'too-many-requests' => 'auth_too_many_requests',
      'network-request-failed' => 'auth_network_error',
      _ => 'auth_unknown_error',
    };
  }
  if (error is GoogleSignInException) {
    return error.code == GoogleSignInExceptionCode.canceled
        ? ''
        : 'auth_google_error';
  }
  return 'auth_unknown_error';
}
