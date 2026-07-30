import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/localization.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../../providers.dart';
import '../../services/authentication_service.dart';

class VerifyEmailScreen extends ConsumerStatefulWidget {
  const VerifyEmailScreen({super.key});

  @override
  ConsumerState<VerifyEmailScreen> createState() => _VerifyEmailScreenState();
}

class _VerifyEmailScreenState extends ConsumerState<VerifyEmailScreen> {
  Timer? _timer;
  int cooldown = 60;
  bool loading = false;
  String? errorKey;
  String? messageKey;

  @override
  void initState() {
    super.initState();
    _startCooldown();
  }

  void _startCooldown() {
    _timer?.cancel();
    cooldown = 60;
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) return;
      if (cooldown <= 1) {
        timer.cancel();
        setState(() => cooldown = 0);
      } else {
        setState(() => cooldown--);
      }
    });
  }

  Future<void> _checkVerification() async {
    var verified = false;
    await _run(() async {
      verified =
          await ref
              .read(authenticationServiceProvider)
              .refreshEmailVerification();
      if (!verified) messageKey = 'verification_still_pending';
    });
    if (verified && mounted) context.go('/stations');
  }

  Future<void> _resend() async {
    var sent = false;
    await _run(() async {
      await ref.read(authenticationServiceProvider).resendEmailVerification();
      sent = true;
      messageKey = 'verification_resent';
    });
    if (sent && mounted) _startCooldown();
  }

  Future<void> _signOut() async {
    await _run(() => ref.read(authenticationServiceProvider).signOut());
  }

  Future<void> _run(Future<void> Function() action) async {
    setState(() {
      loading = true;
      errorKey = null;
      messageKey = null;
    });
    try {
      await action();
    } catch (error) {
      if (mounted) {
        setState(() => errorKey = authenticationErrorKey(error));
      }
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(authStateProvider).value;
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 440),
              child: Column(
                children: [
                  const PranaLogo.lockup(size: 148),
                  const SizedBox(height: 24),
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(22),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          const Icon(
                            Icons.mark_email_unread_outlined,
                            size: 46,
                            color: PranaTheme.brandBlue,
                          ),
                          const SizedBox(height: 14),
                          Text(
                            AppText.of(context, 'verify_email_title'),
                            textAlign: TextAlign.center,
                            style: Theme.of(context).textTheme.titleLarge
                                ?.copyWith(fontWeight: FontWeight.w800),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            AppText.format(context, 'verify_email_body', {
                              'email': user?.email ?? '',
                            }),
                            textAlign: TextAlign.center,
                            style: const TextStyle(color: PranaTheme.muted),
                          ),
                          if (messageKey != null)
                            Padding(
                              padding: const EdgeInsets.only(top: 14),
                              child: Text(
                                AppText.of(context, messageKey!),
                                textAlign: TextAlign.center,
                                style: const TextStyle(
                                  color: Color(0xFF267153),
                                ),
                              ),
                            ),
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
                          const SizedBox(height: 20),
                          FilledButton(
                            onPressed: loading ? null : _checkVerification,
                            child: Text(
                              AppText.of(
                                context,
                                loading ? 'signing_in' : 'verification_check',
                              ),
                            ),
                          ),
                          TextButton(
                            onPressed: loading || cooldown > 0 ? null : _resend,
                            child: Text(
                              cooldown > 0
                                  ? AppText.format(
                                    context,
                                    'verification_resend_wait',
                                    {'seconds': '$cooldown'},
                                  )
                                  : AppText.of(context, 'resend_verification'),
                            ),
                          ),
                          const SizedBox(height: 8),
                          OutlinedButton.icon(
                            onPressed: loading ? null : _signOut,
                            icon: const Icon(Icons.logout),
                            label: Text(AppText.of(context, 'sign_out')),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
