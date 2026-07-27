import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_sign_in/google_sign_in.dart';

import '../../core/app_config.dart';
import '../../core/localization.dart';
import '../../core/widgets.dart';
import '../../providers.dart';

class AccountScreen extends ConsumerStatefulWidget {
  const AccountScreen({super.key});

  @override
  ConsumerState<AccountScreen> createState() => _AccountScreenState();
}

class _AccountScreenState extends ConsumerState<AccountScreen> {
  bool busy = false;
  String? message;
  late Future<Map<String, dynamic>> _accountData;

  @override
  void initState() {
    super.initState();
    _accountData = _load();
  }

  Future<Map<String, dynamic>> _load() async {
    final api = ref.read(apiProvider);
    final values = await Future.wait([
      api.account(),
      api.plans(),
      api.devices(),
      api.stations(),
    ]);
    return {
      'account': values[0],
      'plans': values[1],
      'devices': values[2],
      'stations': values[3],
    };
  }

  Future<void> _refresh() async {
    final next = _load();
    setState(() => _accountData = next);
    await next;
  }

  Future<void> _action(
    Future<void> Function() action, {
    bool refreshData = false,
  }) async {
    setState(() {
      busy = true;
      message = null;
    });
    try {
      await action();
      if (mounted) {
        setState(() {
          message = AppText.of(context, 'done');
          if (refreshData) _accountData = _load();
        });
      }
    } catch (error) {
      if (mounted) setState(() => message = '$error');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> _linkGoogle() async {
    await _action(() async {
      final googleUser = await GoogleSignIn.instance.authenticate();
      final authentication = googleUser.authentication;
      await ref
          .read(authProvider)
          .currentUser
          ?.linkWithCredential(
            GoogleAuthProvider.credential(idToken: authentication.idToken),
          );
    });
  }

  Future<bool> _confirm(String name) async =>
      await showDialog<bool>(
        context: context,
        builder:
            (context) => AlertDialog(
              title: Text(AppText.of(context, 'confirm_revoke')),
              content: Text(name),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(context, false),
                  child: Text(AppText.of(context, 'close')),
                ),
                FilledButton(
                  onPressed: () => Navigator.pop(context, true),
                  child: Text(AppText.of(context, 'revoke')),
                ),
              ],
            ),
      ) ??
      false;

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(authStateProvider).value;
    final locale = ref.watch(appLocaleProvider);
    return Scaffold(
      appBar: PranaPageHeader(
        title: AppText.of(context, 'account_plan'),
        subtitle: 'ACCOUNT CENTER',
      ),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _accountData,
        builder: (context, snapshot) {
          if (!snapshot.hasData) {
            if (snapshot.hasError) {
              return Center(child: Text('${snapshot.error}'));
            }
            return const Center(child: CircularProgressIndicator());
          }
          final data = snapshot.data!;
          final account = Map<String, dynamic>.from(data['account'] as Map);
          final usage = Map<String, dynamic>.from(
            account['usage'] as Map? ?? const {},
          );
          final plans = List<Map<String, dynamic>>.from(data['plans'] as List);
          final devices = List<Map<String, dynamic>>.from(
            data['devices'] as List,
          );
          final stations = List<Map<String, dynamic>>.from(
            data['stations'] as List,
          );
          final providers =
              user?.providerData.map((item) => item.providerId).toSet() ??
              const <String>{};
          final used = (usage['used_audio_seconds'] ?? 0) as num;
          final limit = (usage['audio_seconds_limit'] ?? 0) as num;
          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                _Section(
                  title: AppText.of(context, 'account'),
                  children: [
                    ListTile(
                      leading: const Icon(Icons.person_outline),
                      title: Text(user?.email ?? ''),
                      subtitle: Text(
                        '${account['status'] ?? '—'} • '
                        '${account['plan_id'] ?? '—'}',
                      ),
                    ),
                    ListTile(
                      title: Text(
                        user?.emailVerified == true
                            ? AppText.of(context, 'email_verified')
                            : AppText.of(context, 'email_unverified'),
                      ),
                      trailing:
                          user?.emailVerified == false
                              ? TextButton(
                                onPressed:
                                    busy
                                        ? null
                                        : () => _action(
                                          () => user!.sendEmailVerification(),
                                        ),
                                child: Text(
                                  AppText.of(context, 'resend_verification'),
                                ),
                              )
                              : null,
                    ),
                    ListTile(
                      title: const Text('Google'),
                      subtitle: Text(
                        providers.contains('google.com')
                            ? AppText.of(context, 'linked')
                            : AppText.of(context, 'not_linked'),
                      ),
                      trailing:
                          providers.contains('google.com')
                              ? null
                              : TextButton(
                                onPressed: busy ? null : _linkGoogle,
                                child: Text(AppText.of(context, 'link_google')),
                              ),
                    ),
                    ListTile(
                      title: Text(AppText.of(context, 'reset_password')),
                      trailing: const Icon(Icons.mail_outline),
                      onTap:
                          user?.email == null || busy
                              ? null
                              : () => _action(
                                () => ref
                                    .read(authProvider)
                                    .sendPasswordResetEmail(
                                      email: user!.email!,
                                    ),
                              ),
                    ),
                  ],
                ),
                _Section(
                  title: AppText.of(context, 'usage'),
                  children: [
                    ListTile(
                      title: LinearProgressIndicator(
                        value:
                            limit > 0
                                ? (used / limit).clamp(0, 1).toDouble()
                                : 0,
                      ),
                      subtitle: Text('$used / $limit seconds'),
                    ),
                  ],
                ),
                _Section(
                  title: AppText.of(context, 'plans'),
                  children: [
                    RadioGroup<String>(
                      groupValue: account['plan_id']?.toString(),
                      onChanged: (value) {
                        if (value == null) return;
                        final plan = plans.firstWhere(
                          (item) => item['id'].toString() == value,
                        );
                        if (!busy && plan['availability'] == 'available') {
                          _action(
                            () => ref.read(apiProvider).selectPlan(value),
                            refreshData: true,
                          );
                        }
                      },
                      child: Column(
                        children:
                            plans
                                .map(
                                  (plan) => RadioListTile<String>(
                                    value: plan['id'].toString(),
                                    enabled:
                                        plan['availability'] == 'available',
                                    title: Text(plan['name'].toString()),
                                    subtitle: Text(
                                      '${plan['audio_seconds_limit']} seconds',
                                    ),
                                  ),
                                )
                                .toList(),
                      ),
                    ),
                  ],
                ),
                _Section(
                  title: AppText.of(context, 'devices'),
                  children: [
                    ...devices.map(
                      (device) => ListTile(
                        title: Text(device['name']?.toString() ?? 'Device'),
                        subtitle: Text(device['platform']?.toString() ?? ''),
                        trailing: IconButton(
                          icon: const Icon(Icons.delete_outline),
                          onPressed:
                              busy
                                  ? null
                                  : () async {
                                    if (await _confirm(
                                      device['name']?.toString() ?? 'Device',
                                    )) {
                                      await _action(
                                        () => ref
                                            .read(apiProvider)
                                            .revokeDevice(
                                              (device['id'] ??
                                                      device['device_id'])
                                                  .toString(),
                                            ),
                                        refreshData: true,
                                      );
                                    }
                                  },
                        ),
                      ),
                    ),
                    ...stations.map(
                      (station) => ListTile(
                        leading: const Icon(Icons.radio),
                        title: Text(station['name']?.toString() ?? 'Station'),
                        subtitle: Text(station['platform']?.toString() ?? ''),
                        trailing: IconButton(
                          icon: const Icon(Icons.link_off),
                          onPressed:
                              busy
                                  ? null
                                  : () async {
                                    if (await _confirm(
                                      station['name']?.toString() ?? 'Station',
                                    )) {
                                      await _action(
                                        () => ref
                                            .read(apiProvider)
                                            .revokeStation(
                                              station['station_id'].toString(),
                                            ),
                                        refreshData: true,
                                      );
                                    }
                                  },
                        ),
                      ),
                    ),
                  ],
                ),
                _Section(
                  title: AppText.of(context, 'settings'),
                  children: [
                    ListTile(
                      title: Text(AppText.of(context, 'ui_language')),
                      trailing: SegmentedButton<String>(
                        showSelectedIcon: false,
                        segments: const [
                          ButtonSegment(value: 'vi', label: Text('VI')),
                          ButtonSegment(value: 'en', label: Text('EN')),
                        ],
                        selected: {
                          locale.locale?.languageCode ??
                              Localizations.localeOf(context).languageCode,
                        },
                        onSelectionChanged:
                            (value) => locale.setLocale(value.first),
                      ),
                    ),
                    ListTile(
                      title: Text(AppText.of(context, 'environment')),
                      subtitle: Text(AppConfig.flavor),
                    ),
                  ],
                ),
                if (message != null)
                  Padding(
                    padding: const EdgeInsets.all(12),
                    child: Text(message!),
                  ),
                OutlinedButton.icon(
                  onPressed:
                      busy ? null : () => ref.read(authProvider).signOut(),
                  icon: const Icon(Icons.logout),
                  label: Text(AppText.of(context, 'sign_out')),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({required this.title, required this.children});
  final String title;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) => Card(
    margin: const EdgeInsets.only(bottom: 12),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 4),
          child: Text(title, style: Theme.of(context).textTheme.titleMedium),
        ),
        ...children,
      ],
    ),
  );
}
