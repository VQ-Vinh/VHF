import 'package:prana_mobile/core/service_messages.dart';
import 'package:prana_mobile/l10n/app_localizations.dart';
import 'package:prana_mobile/app/di/auth_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:prana_mobile/core/brand.dart';
import 'package:prana_mobile/data/auth/authentication_service.dart';
import 'package:prana_mobile/features/auth/auth_validation.dart';

enum _AuthMode { signIn, signUp }

class SignInScreen extends ConsumerStatefulWidget {
  const SignInScreen({super.key});

  @override
  ConsumerState<SignInScreen> createState() => _SignInScreenState();
}

class _SignInScreenState extends ConsumerState<SignInScreen>
    with SingleTickerProviderStateMixin {
  final email = TextEditingController();
  final password = TextEditingController();
  final confirmation = TextEditingController();
  final _emailFieldKey = GlobalKey<FormFieldState<String>>();
  late final TabController _tabs;
  var _formKey = GlobalKey<FormState>();
  var mode = _AuthMode.signIn;
  bool loading = false;
  bool submitted = false;
  bool obscurePassword = true;
  bool obscureConfirmation = true;
  String? errorKey;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 2, vsync: this);
    _tabs.addListener(_handleTabChange);
  }

  void _handleTabChange() {
    if (_tabs.indexIsChanging) return;
    final next = _tabs.index == 0 ? _AuthMode.signIn : _AuthMode.signUp;
    if (next == mode) return;
    setState(() {
      mode = next;
      errorKey = null;
      submitted = false;
      _formKey = GlobalKey<FormState>();
    });
  }

  Future<void> _submit() async {
    setState(() {
      submitted = true;
      errorKey = null;
    });
    if (!(_formKey.currentState?.validate() ?? false)) return;

    await _run(() async {
      final service = ref.read(authenticationServiceProvider);
      if (mode == _AuthMode.signUp) {
        await service.signUp(email: email.text.trim(), password: password.text);
      } else {
        await service.signIn(email: email.text.trim(), password: password.text);
      }
    });
  }

  Future<void> _google() async {
    await _run(
      () => ref.read(authenticationServiceProvider).signInWithGoogle(),
    );
  }

  Future<void> _resetPassword() async {
    setState(() {
      errorKey = null;
    });
    if (!isValidEmail(email.text)) {
      _emailFieldKey.currentState?.validate();
      return;
    }
    var sent = false;
    await _run(() async {
      await ref
          .read(authenticationServiceProvider)
          .sendPasswordReset(email.text.trim());
      sent = true;
    });
    if (sent && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(AppLocalizations.of(context).resetSent)),
      );
    }
  }

  Future<void> _run(Future<dynamic> Function() action) async {
    setState(() {
      loading = true;
      errorKey = null;
    });
    try {
      await action();
    } catch (error) {
      if (mounted) {
        final key = authenticationErrorKey(error);
        if (key.isNotEmpty) setState(() => errorKey = key);
      }
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  String? _validateEmail(String? value) {
    final text = value?.trim() ?? '';
    if (text.isEmpty) return AppLocalizations.of(context).authEmailRequired;
    if (!isValidEmail(text)) {
      return AppLocalizations.of(context).authInvalidEmail;
    }
    return null;
  }

  String? _validatePassword(String? value) {
    final text = value ?? '';
    if (text.isEmpty) return AppLocalizations.of(context).authPasswordRequired;
    if (mode == _AuthMode.signUp && !isValidPassword(text)) {
      return AppLocalizations.of(context).authPasswordRequirements;
    }
    return null;
  }

  String? _validateConfirmation(String? value) {
    final text = value ?? '';
    if (text.isEmpty) return AppLocalizations.of(context).authConfirmRequired;
    if (!passwordsMatch(password.text, text)) {
      return AppLocalizations.of(context).authPasswordMismatch;
    }
    return null;
  }

  @override
  void dispose() {
    _tabs
      ..removeListener(_handleTabChange)
      ..dispose();
    email.dispose();
    password.dispose();
    confirmation.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final localeController = ref.watch(appLocaleProvider);
    final signUp = mode == _AuthMode.signUp;
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            Align(
              alignment: Alignment.topRight,
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: SegmentedButton<String>(
                  showSelectedIcon: false,
                  segments: [
                    for (final locale in AppLocalizations.supportedLocales)
                      ButtonSegment(
                        value: locale.languageCode,
                        label: Text(locale.languageCode.toUpperCase()),
                      ),
                  ],
                  selected: {Localizations.localeOf(context).languageCode},
                  onSelectionChanged:
                      loading
                          ? null
                          : (value) => localeController.setLocale(value.first),
                ),
              ),
            ),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(24),
                child: Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 440),
                    child: Column(
                      children: [
                        const PranaLogo.lockup(size: 156),
                        const SizedBox(height: 12),
                        Text(
                          AppLocalizations.of(context).tagline,
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color:
                                Theme.of(context).colorScheme.onSurfaceVariant,
                          ),
                        ),
                        const SizedBox(height: 28),
                        Card(
                          child: Padding(
                            padding: const EdgeInsets.all(20),
                            child: AutofillGroup(
                              child: Form(
                                key: _formKey,
                                autovalidateMode:
                                    submitted
                                        ? AutovalidateMode.onUserInteraction
                                        : AutovalidateMode.disabled,
                                child: Column(
                                  crossAxisAlignment:
                                      CrossAxisAlignment.stretch,
                                  children: [
                                    AbsorbPointer(
                                      absorbing: loading,
                                      child: TabBar(
                                        controller: _tabs,
                                        tabs: [
                                          Padding(
                                            padding: const EdgeInsets.symmetric(
                                              vertical: 12,
                                            ),
                                            child: Text(
                                              AppLocalizations.of(
                                                context,
                                              ).signIn,
                                            ),
                                          ),
                                          Padding(
                                            padding: const EdgeInsets.symmetric(
                                              vertical: 12,
                                            ),
                                            child: Text(
                                              AppLocalizations.of(
                                                context,
                                              ).signUp,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                    const SizedBox(height: 18),
                                    TextFormField(
                                      key: _emailFieldKey,
                                      controller: email,
                                      enabled: !loading,
                                      autofillHints: const [
                                        AutofillHints.email,
                                      ],
                                      keyboardType: TextInputType.emailAddress,
                                      textInputAction: TextInputAction.next,
                                      validator: _validateEmail,
                                      decoration: const InputDecoration(
                                        labelText: 'Email',
                                        prefixIcon: Icon(Icons.mail_outline),
                                      ),
                                    ),
                                    const SizedBox(height: 12),
                                    TextFormField(
                                      controller: password,
                                      enabled: !loading,
                                      obscureText: obscurePassword,
                                      autofillHints: [
                                        signUp
                                            ? AutofillHints.newPassword
                                            : AutofillHints.password,
                                      ],
                                      textInputAction:
                                          signUp
                                              ? TextInputAction.next
                                              : TextInputAction.done,
                                      onFieldSubmitted:
                                          signUp || loading
                                              ? null
                                              : (_) => _submit(),
                                      validator: _validatePassword,
                                      decoration: InputDecoration(
                                        labelText:
                                            AppLocalizations.of(
                                              context,
                                            ).password,
                                        prefixIcon: const Icon(
                                          Icons.lock_outline,
                                        ),
                                        suffixIcon: IconButton(
                                          tooltip:
                                              (obscurePassword
                                                  ? AppLocalizations.of(
                                                    context,
                                                  ).showPassword
                                                  : AppLocalizations.of(
                                                    context,
                                                  ).hidePassword),
                                          onPressed:
                                              loading
                                                  ? null
                                                  : () => setState(
                                                    () =>
                                                        obscurePassword =
                                                            !obscurePassword,
                                                  ),
                                          icon: Icon(
                                            obscurePassword
                                                ? Icons.visibility_outlined
                                                : Icons.visibility_off_outlined,
                                          ),
                                        ),
                                      ),
                                    ),
                                    if (signUp) ...[
                                      const SizedBox(height: 12),
                                      TextFormField(
                                        controller: confirmation,
                                        enabled: !loading,
                                        obscureText: obscureConfirmation,
                                        autofillHints: const [
                                          AutofillHints.newPassword,
                                        ],
                                        textInputAction: TextInputAction.done,
                                        onFieldSubmitted:
                                            loading ? null : (_) => _submit(),
                                        validator: _validateConfirmation,
                                        decoration: InputDecoration(
                                          labelText:
                                              AppLocalizations.of(
                                                context,
                                              ).confirmPassword,
                                          prefixIcon: const Icon(
                                            Icons.lock_reset_outlined,
                                          ),
                                          suffixIcon: IconButton(
                                            tooltip:
                                                (obscureConfirmation
                                                    ? AppLocalizations.of(
                                                      context,
                                                    ).showPassword
                                                    : AppLocalizations.of(
                                                      context,
                                                    ).hidePassword),
                                            onPressed:
                                                loading
                                                    ? null
                                                    : () => setState(
                                                      () =>
                                                          obscureConfirmation =
                                                              !obscureConfirmation,
                                                    ),
                                            icon: Icon(
                                              obscureConfirmation
                                                  ? Icons.visibility_outlined
                                                  : Icons
                                                      .visibility_off_outlined,
                                            ),
                                          ),
                                        ),
                                      ),
                                    ],
                                    if (errorKey != null)
                                      Container(
                                        margin: const EdgeInsets.only(top: 14),
                                        padding: const EdgeInsets.all(11),
                                        decoration: BoxDecoration(
                                          color: const Color(0xFFF9E1E5),
                                          borderRadius: BorderRadius.circular(
                                            9,
                                          ),
                                        ),
                                        child: Text(
                                          localizedServiceMessage(
                                            context,
                                            errorKey!,
                                          ),
                                          style: const TextStyle(
                                            color: Color(0xFFA42A3A),
                                          ),
                                        ),
                                      ),
                                    const SizedBox(height: 18),
                                    FilledButton(
                                      onPressed: loading ? null : _submit,
                                      child: Text(
                                        (loading
                                            ? AppLocalizations.of(
                                              context,
                                            ).signingIn
                                            : signUp
                                            ? AppLocalizations.of(
                                              context,
                                            ).createAccount
                                            : AppLocalizations.of(
                                              context,
                                            ).signIn),
                                      ),
                                    ),
                                    if (!signUp)
                                      TextButton(
                                        onPressed:
                                            loading ? null : _resetPassword,
                                        child: Text(
                                          AppLocalizations.of(
                                            context,
                                          ).forgotPassword,
                                        ),
                                      ),
                                    const SizedBox(height: 10),
                                    OutlinedButton.icon(
                                      onPressed: loading ? null : _google,
                                      icon: const Icon(Icons.login),
                                      label: Text(
                                        (signUp
                                            ? AppLocalizations.of(
                                              context,
                                            ).googleSignUp
                                            : AppLocalizations.of(
                                              context,
                                            ).google),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
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
