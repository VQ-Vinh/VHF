final _values = <String, String>{};
String? readPreference(String key) => _values[key];
void writePreference(String key, String? value) {
  if (value == null) {
    _values.remove(key);
  } else {
    _values[key] = value;
  }
}
