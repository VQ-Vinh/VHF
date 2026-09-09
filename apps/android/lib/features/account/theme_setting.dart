import 'package:flutter/material.dart';
import 'package:prana_mobile/l10n/app_localizations.dart';

class ThemeSetting extends StatelessWidget {
  const ThemeSetting({
    super.key,
    required this.darkMode,
    required this.onChanged,
  });

  final bool darkMode;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) => SwitchListTile.adaptive(
    key: const ValueKey('dark-mode-setting'),
    contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 2),
    secondary: const Icon(Icons.dark_mode_outlined),
    title: Text(AppLocalizations.of(context).darkMode),
    subtitle: Text(AppLocalizations.of(context).darkModeHint),
    value: darkMode,
    onChanged: onChanged,
  );
}
