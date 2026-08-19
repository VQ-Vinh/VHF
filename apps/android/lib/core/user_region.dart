import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// The country and timezone the user picked, used to date stored recordings.
///
/// The server owns this value; secure storage is only a cache so the picker
/// and history queries have something to show before `/v1/me` comes back.
class UserRegionController extends ChangeNotifier {
  UserRegionController(this._storage) {
    _load();
  }

  static const _countryKey = 'user_country';
  static const _timezoneKey = 'user_timezone';

  final FlutterSecureStorage _storage;

  String? countryCode;
  String? timezoneName;

  bool get isSet => (timezoneName ?? '').isNotEmpty;

  Future<void> _load() async {
    final country = await _storage.read(key: _countryKey);
    final timezone = await _storage.read(key: _timezoneKey);
    if ((country ?? '').isEmpty && (timezone ?? '').isEmpty) return;
    countryCode = country;
    timezoneName = timezone;
    notifyListeners();
  }

  /// Adopts what the server reports, so a change made on another device wins.
  Future<void> hydrate({String? country, String? timezone}) async {
    final nextCountry = (country ?? '').isEmpty ? null : country;
    final nextTimezone = (timezone ?? '').isEmpty ? null : timezone;
    if (nextCountry == countryCode && nextTimezone == timezoneName) return;
    await _apply(nextCountry, nextTimezone);
  }

  Future<void> setRegion(String country, String timezone) =>
      _apply(country, timezone);

  Future<void> _apply(String? country, String? timezone) async {
    countryCode = country;
    timezoneName = timezone;
    notifyListeners();
    await _storage.write(key: _countryKey, value: country);
    await _storage.write(key: _timezoneKey, value: timezone);
  }
}

/// One country as offered by `GET /v1/countries`.
class CountryOption {
  const CountryOption({
    required this.code,
    required this.name,
    required this.timezones,
  });

  factory CountryOption.fromJson(Map<String, dynamic> json) => CountryOption(
    code: json['code']?.toString() ?? '',
    name: json['name']?.toString() ?? '',
    timezones:
        (json['timezones'] as List? ?? const [])
            .map((item) => item.toString())
            .toList(),
  );

  final String code;
  final String name;
  final List<String> timezones;

  bool matches(String query) {
    final needle = query.trim().toLowerCase();
    if (needle.isEmpty) return true;
    return name.toLowerCase().contains(needle) ||
        code.toLowerCase().contains(needle) ||
        timezones.any((zone) => zone.toLowerCase().contains(needle));
  }
}
