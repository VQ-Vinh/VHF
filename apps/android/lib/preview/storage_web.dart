import 'dart:js_interop';

@JS('localStorage')
external _Storage get _localStorage;
extension type _Storage(JSObject _) implements JSObject {
  external String? getItem(String key);
  external void setItem(String key, String value);
  external void removeItem(String key);
}

// In a browser that blocks storage, keep the preview usable for this session.
final _fallback = <String, String>{};
String? readPreference(String key) {
  try {
    return _localStorage.getItem(key);
  } catch (_) {
    return _fallback[key];
  }
}

void writePreference(String key, String? value) {
  if (value == null) {
    _fallback.remove(key);
  } else {
    _fallback[key] = value;
  }
  try {
    if (value == null) {
      _localStorage.removeItem(key);
    } else {
      _localStorage.setItem(key, value);
    }
  } catch (_) {
    /* Browser privacy settings can disable persistence. */
  }
}
