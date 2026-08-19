import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_sign_in/google_sign_in.dart';

import '../../core/app_config.dart';
import '../../core/localization.dart';
import '../../core/user_region.dart';
import '../../core/widgets.dart';
import '../../providers.dart';
import '../../services/prana_api.dart';
import '../../services/authentication_service.dart';

class AccountScreen extends ConsumerStatefulWidget {
  const AccountScreen({super.key});

  @override
  ConsumerState<AccountScreen> createState() => _AccountScreenState();
}

class _AccountScreenState extends ConsumerState<AccountScreen> {
  bool busy = false;
  bool showPlans = false;
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
    final account = values[0] as Map<String, dynamic>;
    // The server is the source of truth, so a choice made on another device wins.
    await ref
        .read(userRegionProvider)
        .hydrate(
          country: account['country_code']?.toString(),
          timezone: account['timezone']?.toString(),
        );
    return {
      'account': account,
      'plans': values[1],
      'devices': values[2],
      'stations': values[3],
    };
  }

  Future<void> _pickCountry() async {
    final countries = await ref.read(countriesProvider.future);
    if (!mounted) return;
    final country = await showModalBottomSheet<CountryOption>(
      context: context,
      isScrollControlled: true,
      builder: (_) => _CountryPicker(countries: countries),
    );
    if (country == null || !mounted) return;

    var timezone = country.timezones.firstOrNull;
    if (country.timezones.length > 1) {
      timezone = await showModalBottomSheet<String>(
        context: context,
        isScrollControlled: true,
        builder: (_) => _TimezonePicker(country: country),
      );
      if (timezone == null || !mounted) return;
    }

    await _action(() async {
      final updated = await ref
          .read(apiProvider)
          .updateRegion(countryCode: country.code, timezone: timezone);
      await ref
          .read(userRegionProvider)
          .hydrate(
            country: updated['country_code']?.toString(),
            timezone: updated['timezone']?.toString(),
          );
    }, refreshData: true);
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
      if (mounted) {
        setState(
          () =>
              message =
                  error is PranaApiFailure
                      ? AppText.of(context, error.messageKey)
                      : '$error',
        );
      }
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

  Future<void> _signOut() async {
    final confirmed =
        await showDialog<bool>(
          context: context,
          builder:
              (context) => AlertDialog(
                title: Text(AppText.of(context, 'confirm_sign_out')),
                content: Text(AppText.of(context, 'confirm_sign_out_body')),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.pop(context, false),
                    child: Text(AppText.of(context, 'close')),
                  ),
                  FilledButton(
                    onPressed: () => Navigator.pop(context, true),
                    child: Text(AppText.of(context, 'sign_out')),
                  ),
                ],
              ),
        ) ??
        false;
    if (!confirmed || !mounted) return;
    setState(() {
      busy = true;
      message = null;
    });
    try {
      await ref.read(authenticationServiceProvider).signOut();
    } catch (error) {
      if (mounted) {
        setState(() {
          message = AppText.of(context, authenticationErrorKey(error));
        });
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<bool> _confirm(String name, {bool removingStation = false}) async =>
      await showDialog<bool>(
        context: context,
        builder:
            (context) => AlertDialog(
              title: Text(
                AppText.of(
                  context,
                  removingStation ? 'confirm_remove_station' : 'confirm_revoke',
                ),
              ),
              content: Text(
                removingStation
                    ? AppText.format(context, 'remove_station_body', {
                      'name': name,
                    })
                    : name,
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(context, false),
                  child: Text(AppText.of(context, 'close')),
                ),
                FilledButton(
                  onPressed: () => Navigator.pop(context, true),
                  child: Text(
                    AppText.of(
                      context,
                      removingStation ? 'remove_station' : 'revoke',
                    ),
                  ),
                ),
              ],
            ),
      ) ??
      false;

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(authStateProvider).value;
    final locale = ref.watch(appLocaleProvider);
    final region = ref.watch(userRegionProvider);
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
          final planId = account['plan_id']?.toString() ?? '';
          final matchingPlans = plans.where(
            (plan) => plan['id']?.toString() == planId,
          );
          final planName =
              matchingPlans.isEmpty
                  ? planId
                  : matchingPlans.first['name']?.toString() ?? planId;
          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                _Section(
                  title: AppText.of(context, 'account'),
                  children: [
                    Padding(
                      padding: const EdgeInsets.fromLTRB(14, 2, 14, 12),
                      child: Row(
                        children: [
                          const CircleAvatar(
                            radius: 20,
                            child: Icon(Icons.person_outline, size: 22),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  user?.email ?? '',
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style:
                                      Theme.of(context).textTheme.titleMedium,
                                ),
                                const SizedBox(height: 6),
                                Wrap(
                                  spacing: 6,
                                  runSpacing: 6,
                                  children: [
                                    _StatusChip(
                                      icon: Icons.check_circle_outline,
                                      label:
                                          account['status']?.toString() ?? '—',
                                    ),
                                    _StatusChip(
                                      icon:
                                          user?.emailVerified == true
                                              ? Icons.verified_outlined
                                              : Icons.warning_amber_outlined,
                                      label:
                                          user?.emailVerified == true
                                              ? AppText.of(
                                                context,
                                                'email_verified',
                                              )
                                              : AppText.of(
                                                context,
                                                'email_unverified',
                                              ),
                                    ),
                                    _StatusChip(
                                      icon: Icons.g_mobiledata,
                                      label:
                                          providers.contains('google.com')
                                              ? AppText.of(context, 'linked')
                                              : AppText.of(
                                                context,
                                                'not_linked',
                                              ),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    const Divider(height: 1),
                    Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 2,
                      ),
                      child: Wrap(
                        spacing: 4,
                        runSpacing: 2,
                        children: [
                          if (user?.emailVerified == false)
                            TextButton.icon(
                              onPressed:
                                  busy
                                      ? null
                                      : () => _action(
                                        () => user!.sendEmailVerification(),
                                      ),
                              icon: const Icon(Icons.mark_email_read_outlined),
                              label: Text(
                                AppText.of(context, 'resend_verification'),
                              ),
                            ),
                          if (!providers.contains('google.com'))
                            TextButton.icon(
                              onPressed: busy ? null : _linkGoogle,
                              icon: const Icon(Icons.link),
                              label: Text(AppText.of(context, 'link_google')),
                            ),
                          TextButton.icon(
                            onPressed:
                                user?.email == null || busy
                                    ? null
                                    : () => _action(
                                      () => ref
                                          .read(authProvider)
                                          .sendPasswordResetEmail(
                                            email: user!.email!,
                                          ),
                                    ),
                            icon: const Icon(Icons.mail_outline),
                            label: Text(
                              AppText.of(context, 'reset_password_short'),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                _Section(
                  title: AppText.of(context, 'plans'),
                  children: [
                    Padding(
                      padding: const EdgeInsets.fromLTRB(14, 0, 14, 12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      planName,
                                      style:
                                          Theme.of(
                                            context,
                                          ).textTheme.titleMedium,
                                    ),
                                    Text(
                                      '${_number(used)} / ${_number(limit)} '
                                      '${AppText.of(context, 'seconds')}',
                                      style: const TextStyle(
                                        color: Color(0xFF65767D),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              TextButton.icon(
                                onPressed:
                                    busy
                                        ? null
                                        : () => setState(
                                          () => showPlans = !showPlans,
                                        ),
                                icon: Icon(
                                  showPlans
                                      ? Icons.expand_less
                                      : Icons.swap_horiz,
                                ),
                                label: Text(
                                  AppText.of(
                                    context,
                                    showPlans ? 'collapse' : 'change_plan',
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 10),
                          LinearProgressIndicator(
                            value:
                                limit > 0
                                    ? (used / limit).clamp(0, 1).toDouble()
                                    : 0,
                            minHeight: 5,
                            borderRadius: BorderRadius.circular(99),
                          ),
                        ],
                      ),
                    ),
                    if (showPlans) ...[
                      const Divider(height: 1),
                      RadioGroup<String>(
                        groupValue: planId,
                        onChanged: (value) {
                          if (value == null || value == planId) return;
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
                                      dense: true,
                                      visualDensity: const VisualDensity(
                                        vertical: -3,
                                      ),
                                      value: plan['id'].toString(),
                                      enabled:
                                          plan['availability'] == 'available',
                                      title: Text(plan['name'].toString()),
                                      subtitle: Text(
                                        '${_number((plan['audio_seconds_limit'] ?? 0) as num)} '
                                        '${AppText.of(context, 'seconds')}',
                                      ),
                                    ),
                                  )
                                  .toList(),
                        ),
                      ),
                    ],
                  ],
                ),
                _Section(
                  title: AppText.of(context, 'devices'),
                  children: [
                    ...devices.map(
                      (device) => ListTile(
                        dense: true,
                        visualDensity: const VisualDensity(vertical: -2),
                        leading: const Icon(Icons.devices_outlined),
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
                        dense: true,
                        visualDensity: const VisualDensity(vertical: -2),
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
                                      removingStation: true,
                                    )) {
                                      await _action(
                                        () => ref
                                            .read(apiProvider)
                                            .removeStation(
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
                      dense: true,
                      visualDensity: const VisualDensity(vertical: -2),
                      title: Text(AppText.of(context, 'ui_language')),
                      trailing: _LanguageToggle(
                        value:
                            locale.locale?.languageCode ??
                            Localizations.localeOf(context).languageCode,
                        onChanged: locale.setLocale,
                      ),
                    ),
                    ListTile(
                      dense: true,
                      visualDensity: const VisualDensity(vertical: -2),
                      title: Text(AppText.of(context, 'country')),
                      subtitle:
                          region.timezoneName == null
                              ? null
                              : Text(region.timezoneName!),
                      trailing: const Icon(Icons.chevron_right, size: 20),
                      onTap: busy ? null : _pickCountry,
                    ),
                    ListTile(
                      dense: true,
                      visualDensity: const VisualDensity(vertical: -3),
                      title: Text(AppText.of(context, 'environment')),
                      trailing: Text(AppConfig.flavor),
                    ),
                  ],
                ),
                if (message != null)
                  Padding(
                    padding: const EdgeInsets.all(12),
                    child: Text(message!),
                  ),
                OutlinedButton.icon(
                  onPressed: busy ? null : _signOut,
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

  static String _number(num value) =>
      value == value.roundToDouble()
          ? value.toInt().toString()
          : value.toStringAsFixed(1);
}

class _Section extends StatelessWidget {
  const _Section({required this.title, required this.children});
  final String title;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) => Card(
    margin: const EdgeInsets.only(bottom: 10),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(14, 11, 14, 6),
          child: Text(
            title,
            style: Theme.of(
              context,
            ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
          ),
        ),
        ...children,
      ],
    ),
  );
}

/// Searchable country list. A plain dropdown is unusable at this length.
class _CountryPicker extends StatefulWidget {
  const _CountryPicker({required this.countries});

  final List<CountryOption> countries;

  @override
  State<_CountryPicker> createState() => _CountryPickerState();
}

class _CountryPickerState extends State<_CountryPicker> {
  String query = '';

  @override
  Widget build(BuildContext context) {
    final matches =
        widget.countries.where((item) => item.matches(query)).toList();
    return _PickerSheet(
      title: AppText.of(context, 'select_country'),
      header: TextField(
        autofocus: true,
        decoration: InputDecoration(
          prefixIcon: const Icon(Icons.search, size: 20),
          hintText: AppText.of(context, 'country_search_hint'),
          isDense: true,
          border: const OutlineInputBorder(),
        ),
        onChanged: (value) => setState(() => query = value),
      ),
      itemCount: matches.length,
      itemBuilder:
          (context, index) => ListTile(
            dense: true,
            title: Text(matches[index].name),
            subtitle:
                matches[index].timezones.length == 1
                    ? Text(matches[index].timezones.first)
                    : null,
            onTap: () => Navigator.pop(context, matches[index]),
          ),
    );
  }
}

/// Second step, shown only for countries that span more than one zone.
class _TimezonePicker extends StatelessWidget {
  const _TimezonePicker({required this.country});

  final CountryOption country;

  @override
  Widget build(BuildContext context) {
    return _PickerSheet(
      title: AppText.of(context, 'select_timezone'),
      itemCount: country.timezones.length,
      itemBuilder:
          (context, index) => ListTile(
            dense: true,
            title: Text(country.timezones[index]),
            onTap: () => Navigator.pop(context, country.timezones[index]),
          ),
    );
  }
}

class _PickerSheet extends StatelessWidget {
  const _PickerSheet({
    required this.title,
    required this.itemCount,
    required this.itemBuilder,
    this.header,
  });

  final String title;
  final int itemCount;
  final IndexedWidgetBuilder itemBuilder;
  final Widget? header;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return SafeArea(
      child: Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(context).viewInsets.bottom,
        ),
        child: SizedBox(
          height: MediaQuery.of(context).size.height * 0.7,
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(title, style: theme.textTheme.titleMedium),
                    const SizedBox(height: 4),
                    Text(
                      AppText.of(context, 'country_change_notice'),
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                    if (header != null) ...[
                      const SizedBox(height: 12),
                      header!,
                    ],
                  ],
                ),
              ),
              const Divider(height: 1),
              Expanded(
                child: ListView.builder(
                  itemCount: itemCount,
                  itemBuilder: itemBuilder,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _LanguageToggle extends StatelessWidget {
  const _LanguageToggle({required this.value, required this.onChanged});

  final String value;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      height: 32,
      padding: const EdgeInsets.all(2),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(99),
        border: Border.all(color: theme.colorScheme.outlineVariant),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _LanguageOption(
            label: 'VI',
            selected: value == 'vi',
            onTap: () => onChanged('vi'),
          ),
          _LanguageOption(
            label: 'EN',
            selected: value == 'en',
            onTap: () => onChanged('en'),
          ),
        ],
      ),
    );
  }
}

class _LanguageOption extends StatelessWidget {
  const _LanguageOption({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return ClipRRect(
      borderRadius: BorderRadius.circular(99),
      child: Material(
        color:
            selected ? theme.colorScheme.secondaryContainer : Colors.transparent,
        child: InkWell(
          onTap: onTap,
          child: Container(
            alignment: Alignment.center,
            width: 44,
            height: 28,
            child: Text(
              label,
              style: theme.textTheme.labelLarge?.copyWith(
                color:
                    selected
                        ? theme.colorScheme.onSecondaryContainer
                        : theme.colorScheme.onSurfaceVariant,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
    decoration: BoxDecoration(
      color: const Color(0xFFEAF2F5),
      borderRadius: BorderRadius.circular(99),
    ),
    child: Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 14, color: const Color(0xFF315F72)),
        const SizedBox(width: 4),
        Text(
          label,
          style: const TextStyle(
            color: Color(0xFF315F72),
            fontSize: 11,
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    ),
  );
}
