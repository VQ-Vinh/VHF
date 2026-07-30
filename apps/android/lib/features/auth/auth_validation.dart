bool isValidEmail(String value) {
  final email = value.trim();
  final at = email.indexOf('@');
  if (at <= 0 || at != email.lastIndexOf('@')) return false;
  final domain = email.substring(at + 1);
  return domain.contains('.') &&
      !domain.startsWith('.') &&
      !domain.endsWith('.');
}

bool isValidPassword(String value) =>
    value.length >= 6 &&
    RegExp('[A-Z]').hasMatch(value) &&
    RegExp('[A-Za-z]').hasMatch(value) &&
    RegExp('[0-9]').hasMatch(value);

bool passwordsMatch(String password, String confirmation) =>
    confirmation.isNotEmpty && password == confirmation;
