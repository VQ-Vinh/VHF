import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class AppThemeModeController extends ChangeNotifier {
  AppThemeModeController(this._storage) {
    ready = _load();
  }

  static const _key = 'dark_mode';
  final FlutterSecureStorage _storage;
  late final Future<void> ready;
  bool darkMode = false;
  bool _disposed = false;
  int _revision = 0;
  Future<void> _writes = Future.value();

  ThemeMode get themeMode => darkMode ? ThemeMode.dark : ThemeMode.light;

  Future<void> _load() async {
    final revision = _revision;
    final value = await _storage.read(key: _key);
    if (_disposed || revision != _revision) return;
    darkMode = value == 'true';
    notifyListeners();
  }

  Future<void> setDarkMode(bool value) async {
    if (_disposed || darkMode == value) return;
    _revision++;
    darkMode = value;
    notifyListeners();
    _writes = _writes
        .catchError((Object _) {})
        .then((_) => _storage.write(key: _key, value: '$value'));
    await _writes;
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}
