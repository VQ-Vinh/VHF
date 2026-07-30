import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/localization.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../../providers.dart';
import '../../services/authentication_service.dart';
import 'auth_validation.dart';

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
        SnackBar(content: Text(AppText.of(context, 'reset_sent'))),
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
    if (text.isEmpty) return AppText.of(context, 'auth_email_required');
    if (!isValidEmail(text)) {
      return AppText.of(context, 'auth_invalid_email');
    }
    return null;
  }

  String? _validatePassword(String? value) {
    final text = value ?? '';
    if (text.isEmpty) return AppText.of(context, 'auth_password_required');
    if (mode == _AuthMode.signUp && !isValidPassword(text)) {
      return AppText.of(context, 'auth_password_requirements');
    }
    return null;
  }

  String? _validateConfirmation(String? value) {
    final text = value ?? '';
    if (text.isEmpty) return AppText.of(context, 'auth_confirm_required');
    if (!passwordsMatch(password.text, text)) {
      return AppText.of(context, 'auth_password_mismatch');
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
                      loading
                          ? null
                          : (value) => localeController.setLocale(value.first),
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
                            child: Form(
                              key: _formKey,
                              autovalidateMode:
                                  submitted
                                      ? AutovalidateMode.onUserInteraction
                                      : AutovalidateMode.disabled,
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.stretch,
                                children: [
                                  AbsorbPointer(
                                    absorbing: loading,
                                    child: TabBar(
                                      controller: _tabs,
                                      tabs: [
                                        Tab(
                                          text: AppText.of(context, 'sign_in'),
                                        ),
                                        Tab(
                                          text: AppText.of(context, 'sign_up'),
                                        ),
                                      ],
                                    ),
                                  ),
                                  const SizedBox(height: 18),
                                  TextFormField(
                                    key: _emailFieldKey,
                                    controller: email,
                                    enabled: !loading,
                                    autofillHints: const [AutofillHints.email],
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
                                      labelText: AppText.of(
                                        context,
                                        'password',
                                      ),
                                      prefixIcon: const Icon(
                                        Icons.lock_outline,
                                      ),
                                      suffixIcon: IconButton(
                                        tooltip: AppText.of(
                                          context,
                                          obscurePassword
                                              ? 'show_password'
                                              : 'hide_password',
                                        ),
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
                                        labelText: AppText.of(
                                          context,
                                          'confirm_password',
                                        ),
                                        prefixIcon: const Icon(
                                          Icons.lock_reset_outlined,
                                        ),
                                        suffixIcon: IconButton(
                                          tooltip: AppText.of(
                                            context,
                                            obscureConfirmation
                                                ? 'show_password'
                                                : 'hide_password',
                                          ),
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
                                                : Icons.visibility_off_outlined,
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
                                        borderRadius: BorderRadius.circular(9),
                                      ),
                                      child: Text(
                                        AppText.of(context, errorKey!),
                                        style: const TextStyle(
                                          color: Color(0xFFA42A3A),
                                        ),
                                      ),
                                    ),
                                  const SizedBox(height: 18),
                                  FilledButton(
                                    onPressed: loading ? null : _submit,
                                    child: Text(
                                      AppText.of(
                                        context,
                                        loading
                                            ? 'signing_in'
                                            : signUp
                                            ? 'create_account'
                                            : 'sign_in',
                                      ),
                                    ),
                                  ),
                                  if (!signUp)
                                    TextButton(
                                      onPressed:
                                          loading ? null : _resetPassword,
                                      child: Text(
                                        AppText.of(context, 'forgot_password'),
                                      ),
                                    ),
                                  const SizedBox(height: 10),
                                  OutlinedButton.icon(
                                    onPressed: loading ? null : _google,
                                    icon: const Icon(Icons.login),
                                    label: Text(
                                      AppText.of(
                                        context,
                                        signUp ? 'google_sign_up' : 'google',
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
              ),
            ),
          ],
        ),
      ),
    );
  }
}
