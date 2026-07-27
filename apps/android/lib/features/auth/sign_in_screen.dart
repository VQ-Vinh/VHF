import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_sign_in/google_sign_in.dart';

import '../../core/localization.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../../providers.dart';

class SignInScreen extends ConsumerStatefulWidget {
  const SignInScreen({super.key});
  @override
  ConsumerState<SignInScreen> createState() => _SignInScreenState();
}

class _SignInScreenState extends ConsumerState<SignInScreen> {
  final email = TextEditingController();
  final password = TextEditingController();
  bool loading = false;
  String? error;

  Future<void> submit({required bool create}) async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final auth = ref.read(authProvider);
      if (create) {
        await auth.createUserWithEmailAndPassword(
          email: email.text.trim(),
          password: password.text,
        );
        await auth.currentUser?.sendEmailVerification();
      } else {
        await auth.signInWithEmailAndPassword(
          email: email.text.trim(),
          password: password.text,
        );
      }
    } on FirebaseAuthException catch (exception) {
      if (mounted) setState(() => error = exception.message ?? exception.code);
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Future<void> google() async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final googleUser = await GoogleSignIn.instance.authenticate();
      final googleAuth = googleUser.authentication;
      await ref
          .read(authProvider)
          .signInWithCredential(
            GoogleAuthProvider.credential(idToken: googleAuth.idToken),
          );
    } on GoogleSignInException catch (exception) {
      if (exception.code != GoogleSignInExceptionCode.canceled && mounted) {
        setState(() => error = exception.description ?? exception.code.name);
      }
    } on FirebaseAuthException catch (exception) {
      if (mounted) setState(() => error = exception.message ?? exception.code);
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Future<void> resetPassword() async {
    if (email.text.trim().isEmpty) return;
    setState(() {
      loading = true;
      error = null;
    });
    try {
      await ref
          .read(authProvider)
          .sendPasswordResetEmail(email: email.text.trim());
      if (mounted) {
        setState(() => error = AppText.of(context, 'reset_sent'));
      }
    } on FirebaseAuthException catch (exception) {
      if (mounted) setState(() => error = exception.message ?? exception.code);
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  void dispose() {
    email.dispose();
    password.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final localeController = ref.watch(appLocaleProvider);
    return Scaffold(
      body: SafeArea(
        child: Stack(
          children: [
            Align(
              alignment: Alignment.topRight,
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: SegmentedButton<String>(
                  showSelectedIcon: false,
                  segments: const [
                    ButtonSegment(value: 'vi', label: Text('VI')),
                    ButtonSegment(value: 'en', label: Text('EN')),
                  ],
                  selected: {Localizations.localeOf(context).languageCode},
                  onSelectionChanged:
                      (value) => localeController.setLocale(value.first),
                ),
              ),
            ),
            Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(24, 72, 24, 24),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 440),
                  child: Column(
                    children: [
                      const PranaLogo.lockup(size: 156),
                      const SizedBox(height: 12),
                      Text(
                        AppText.of(context, 'tagline'),
                        textAlign: TextAlign.center,
                        style: const TextStyle(color: PranaTheme.muted),
                      ),
                      const SizedBox(height: 28),
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(20),
                          child: AutofillGroup(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                Text(
                                  AppText.of(context, 'sign_in').toUpperCase(),
                                  style: const TextStyle(
                                    fontSize: 12,
                                    letterSpacing: 1,
                                    fontWeight: FontWeight.w800,
                                    color: PranaTheme.brandBlue,
                                  ),
                                ),
                                const SizedBox(height: 16),
                                TextField(
                                  controller: email,
                                  autofillHints: const [AutofillHints.email],
                                  keyboardType: TextInputType.emailAddress,
                                  decoration: const InputDecoration(
                                    labelText: 'Email',
                                    prefixIcon: Icon(Icons.mail_outline),
                                  ),
                                ),
                                const SizedBox(height: 12),
                                TextField(
                                  controller: password,
                                  obscureText: true,
                                  autofillHints: const [AutofillHints.password],
                                  decoration: InputDecoration(
                                    labelText: AppText.of(context, 'password'),
                                    prefixIcon: const Icon(Icons.lock_outline),
                                  ),
                                ),
                                if (error != null)
                                  Container(
                                    margin: const EdgeInsets.only(top: 14),
                                    padding: const EdgeInsets.all(11),
                                    decoration: BoxDecoration(
                                      color: const Color(0xFFF9E1E5),
                                      borderRadius: BorderRadius.circular(9),
                                    ),
                                    child: Text(
                                      error!,
                                      style: const TextStyle(
                                        color: Color(0xFFA42A3A),
                                      ),
                                    ),
                                  ),
                                const SizedBox(height: 18),
                                FilledButton(
                                  onPressed:
                                      loading
                                          ? null
                                          : () => submit(create: false),
                                  child: Text(
                                    AppText.of(
                                      context,
                                      loading ? 'signing_in' : 'sign_in',
                                    ),
                                  ),
                                ),
                                TextButton(
                                  onPressed: loading ? null : resetPassword,
                                  child: Text(
                                    AppText.of(context, 'forgot_password'),
                                  ),
                                ),
                                const SizedBox(height: 10),
                                OutlinedButton.icon(
                                  onPressed: loading ? null : google,
                                  icon: const Icon(Icons.login),
                                  label: Text(AppText.of(context, 'google')),
                                ),
                                TextButton(
                                  onPressed:
                                      loading
                                          ? null
                                          : () => submit(create: true),
                                  child: Text(
                                    AppText.of(context, 'create_account'),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
