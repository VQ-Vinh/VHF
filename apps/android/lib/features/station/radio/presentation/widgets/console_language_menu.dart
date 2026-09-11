import 'package:flutter/material.dart';
import 'package:prana_mobile/core/languages.dart';
import 'console_palette.dart';

/// Language picker drawn as console text with a chevron, not a form field.
///
/// Shared by TRANSLATE TO on the RX strip and TRANSMIT IN on the TX dock, which
/// used to be a DropdownButtonFormField and a hand-built PopupMenuButton that
/// had to be kept looking alike by hand.
class ConsoleLanguageMenu extends StatelessWidget {
  const ConsoleLanguageMenu({
    super.key,
    required this.value,
    required this.enabled,
    required this.onSelected,
    required this.tooltip,
    this.valueKey,
    this.chevronKey,
  });

  final String value;
  final bool enabled;
  final ValueChanged<String> onSelected;
  final String tooltip;
  final Key? valueKey;
  final Key? chevronKey;

  @override
  Widget build(BuildContext context) {
    final palette = ConsolePalette.of(context);
    final ink = enabled ? palette.ink : palette.muted;
    return PopupMenuButton<String>(
      enabled: enabled,
      padding: EdgeInsets.zero,
      position: PopupMenuPosition.over,
      tooltip: tooltip,
      onSelected: onSelected,
      itemBuilder:
          (context) => [
            for (final entry in supportedLanguages.entries)
              PopupMenuItem<String>(
                value: entry.key,
                child: Row(
                  children: [
                    Expanded(child: Text(entry.value)),
                    if (entry.key == value)
                      Icon(Icons.check, size: 18, color: palette.accent),
                  ],
                ),
              ),
          ],
      child: ConstrainedBox(
        constraints: const BoxConstraints(minHeight: 48),
        child: Row(
          children: [
            Expanded(
              child: Text(
                supportedLanguages[value] ?? value.toUpperCase(),
                key: valueKey,
                style: TextStyle(
                  fontFamily: consoleLabel,
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                  color: ink,
                ),
              ),
            ),
            Icon(
              Icons.keyboard_arrow_down,
              key: chevronKey,
              color: enabled ? palette.accent : palette.muted,
            ),
          ],
        ),
      ),
    );
  }
}
