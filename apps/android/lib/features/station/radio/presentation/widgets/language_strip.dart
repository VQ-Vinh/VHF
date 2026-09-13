part of '../live_screen.dart';

/// Heard language, an arrow, and the language it is translated into, read as
/// one direction across the strip rather than as two form fields.
class LanguageStrip extends StatelessWidget {
  const LanguageStrip({
    super.key,
    required this.detectedLanguage,
    required this.targetLanguage,
    required this.enabled,
    required this.onChanged,
  });

  final String? detectedLanguage;
  final String targetLanguage;
  final bool enabled;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = ConsolePalette.of(context);
    final code = detectedLanguage;
    final heard = ConsoleField(
      key: const ValueKey('input-language-field'),
      caption: l10n.rxHeard,
      // The name alone. The two-letter code said the same thing twice, and
      // the row is about the direction, not about codes.
      child: Text(
        code == null
            ? l10n.detecting
            : supportedLanguages[code] ?? code.toUpperCase(),
        style: TextStyle(
          fontFamily: consoleLabel,
          fontSize: 15,
          fontWeight: FontWeight.w600,
          color: code == null ? palette.muted : palette.ink,
        ),
      ),
    );
    final target = ConsoleField(
      key: const ValueKey('output-language-field'),
      caption: l10n.rxTranslateTo,
      child: ConsoleLanguageMenu(
        value:
            supportedLanguages.containsKey(targetLanguage)
                ? targetLanguage
                : 'en',
        enabled: enabled,
        onSelected: onChanged,
        tooltip: l10n.rxTranslateTo,
      ),
    );
    return Container(
      key: const ValueKey('rx-language-strip'),
      decoration: BoxDecoration(
        color: palette.panel,
        border: Border(bottom: BorderSide(color: palette.hairline)),
      ),
      padding: const EdgeInsets.fromLTRB(14, 10, 14, 4),
      child: LayoutBuilder(
        builder: (context, constraints) {
          // Side by side while each field keeps room for a language name; under
          // a large text scale they stack, because a name squeezed into half a
          // phone breaks mid-word ("Englis" / "h").
          final inline =
              constraints.maxWidth >=
              MediaQuery.textScalerOf(context).scale(118) * 2 + 50;
          if (!inline) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              mainAxisSize: MainAxisSize.min,
              children: [
                heard,
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 2),
                  child: Align(
                    alignment: AlignmentDirectional.centerStart,
                    child: ExcludeSemantics(
                      child: Icon(
                        Icons.arrow_downward,
                        size: 18,
                        color: palette.accent,
                      ),
                    ),
                  ),
                ),
                target,
              ],
            );
          }
          return IntrinsicHeight(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Both sides Expanded at the same flex, so the two fields stay
                // the same width whatever the arrow and rules between them
                // take. The arrow sits in its own bay: rule, arrow, rule.
                Expanded(child: heard),
                VerticalDivider(
                  width: 13,
                  thickness: 1,
                  color: palette.hairline,
                ),
                Center(
                  child: ExcludeSemantics(
                    child: Icon(
                      Icons.arrow_forward,
                      size: 18,
                      color: palette.accent,
                    ),
                  ),
                ),
                VerticalDivider(
                  width: 13,
                  thickness: 1,
                  color: palette.hairline,
                ),
                Expanded(child: target),
              ],
            ),
          );
        },
      ),
    );
  }
}
