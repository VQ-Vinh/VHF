import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'storage_memory.dart'
    if (dart.library.js_interop) 'storage_web.dart'
    as browser;

/// Same controller contract, separate namespace from any mobile credentials.
/// Only visual preferences persist. Country and other demo data reset per session.
class PreviewStorage extends FlutterSecureStorage {
  final _session = <String, String>{};
  bool _persistent(String key) => key == 'app_locale' || key == 'dark_mode';
  @override
  Future<String?> read({
    required String key,
    AppleOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    AppleOptions? mOptions,
    WindowsOptions? wOptions,
  }) async =>
      _persistent(key)
          ? browser.readPreference('prana.ui-preview.$key')
          : _session[key];
  @override
  Future<void> write({
    required String key,
    required String? value,
    AppleOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    AppleOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    if (_persistent(key)) {
      browser.writePreference('prana.ui-preview.$key', value);
    } else if (value == null) {
      _session.remove(key);
    } else {
      _session[key] = value;
    }
  }
}
