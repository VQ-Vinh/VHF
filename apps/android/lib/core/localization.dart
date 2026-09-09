import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:prana_mobile/l10n/app_localizations.dart';

abstract final class CountryLocalePolicy {
  static const _languages = {'VN': 'vi'};

  static List<Locale> choices(String? country) {
    final supported = AppLocalizations.supportedLocales;
    if (country == null || country.trim().isEmpty) {
      return [
        const Locale('en'),
        ...supported.where((l) => l.languageCode != 'en'),
      ];
    }
    final code = _languages[country.toUpperCase()];
    return [
      const Locale('en'),
      ...supported.where((l) => l.languageCode == code && code != 'en'),
    ];
  }

  static Locale reconcile(Locale current, String? country) {
    final allowed = choices(country);
    return allowed.firstWhere(
      (l) => l.languageCode == current.languageCode,
      orElse: () => allowed.last,
    );
  }
}

Locale resolveAppLocale(Locale? locale, Iterable<Locale> supported) =>
    supported.firstWhere(
      (l) => l.languageCode == locale?.languageCode,
      orElse: () => const Locale('en'),
    );

class AppLocaleController extends ChangeNotifier {
  AppLocaleController(this._storage) {
    ready = _load();
  }
  static const _key = 'app_locale';
  final FlutterSecureStorage _storage;
  late final Future<void> ready;
  Locale? locale;
  String? _country;
  bool _disposed = false;
  int _revision = 0;
  Future<void> _writes = Future.value();

  Future<void> _load() async {
    final revision = _revision;
    final value = await _storage.read(key: _key);
    if (_disposed || revision != _revision) return;
    final saved = resolveAppLocale(
      value == null ? null : Locale(value),
      AppLocalizations.supportedLocales,
    );
    locale = CountryLocalePolicy.reconcile(saved, _country);
    notifyListeners();
    if (value != null && locale!.languageCode != value) await _persist();
  }

  Future<void> _persist() {
    final code = locale!.languageCode;
    return _writes = _writes
        .catchError((Object _) {})
        .then((_) => _storage.write(key: _key, value: code));
  }

  Future<void> setLocale(String code) async {
    if (_disposed) return;
    _revision++;
    locale = resolveAppLocale(Locale(code), AppLocalizations.supportedLocales);
    notifyListeners();
    await _persist();
  }

  Future<void> reconcileCountry(String? country) async {
    _country = country;
    if (_disposed || locale == null) return;
    final next = CountryLocalePolicy.reconcile(locale!, country);
    if (next == locale) return;
    await setLocale(next.languageCode);
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}
