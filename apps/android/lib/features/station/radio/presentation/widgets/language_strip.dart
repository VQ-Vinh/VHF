part of '../live_screen.dart';

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
  Widget build(BuildContext context) => Container(
    key: const ValueKey('rx-language-strip'),
    color: Theme.of(context).colorScheme.surfaceContainerLow,
    padding: const EdgeInsets.fromLTRB(10, 6, 10, 8),
    child: AdaptiveFields(
      minimumWidth: 140,
      children: [
        SizedBox(
          child: _LanguageValue(
            key: const ValueKey('input-language-field'),
            label: AppLocalizations.of(context).rxHeard,
            value:
                detectedLanguage == null
                    ? AppLocalizations.of(context).detecting
                    : supportedLanguages[detectedLanguage] ??
                        detectedLanguage!.toUpperCase(),
          ),
        ),
        SizedBox(
          child: Column(
            key: const ValueKey('output-language-field'),
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              _LanguageLabel(label: AppLocalizations.of(context).rxTranslateTo),
              const SizedBox(height: 1),
              ConstrainedBox(
                constraints: const BoxConstraints(minHeight: 48),
                child: DropdownButtonFormField<String>(
                  key: ValueKey(targetLanguage),
                  initialValue:
                      supportedLanguages.containsKey(targetLanguage)
                          ? targetLanguage
                          : 'en',
                  isExpanded: true,
                  itemHeight: null,
                  decoration: const InputDecoration(
                    isDense: true,
                    contentPadding: EdgeInsets.symmetric(
                      horizontal: 11,
                      vertical: 8,
                    ),
                  ),
                  items:
                      supportedLanguages.entries
                          .map(
                            (entry) => DropdownMenuItem(
                              value: entry.key,
                              child: Text(entry.value),
                            ),
                          )
                          .toList(),
                  onChanged:
                      enabled
                          ? (value) {
                            if (value != null) onChanged(value);
                          }
                          : null,
                ),
              ),
            ],
          ),
        ),
      ],
    ),
  );
}

class _LanguageLabel extends StatelessWidget {
  const _LanguageLabel({required this.label});
  final String label;

  @override
  Widget build(BuildContext context) => Text(
    label.toUpperCase(),

    style: TextStyle(
      color: Theme.of(context).colorScheme.onSurfaceVariant,
      fontSize: 10,
      fontWeight: FontWeight.w800,
      letterSpacing: .7,
    ),
  );
}

class _LanguageValue extends StatelessWidget {
  const _LanguageValue({super.key, required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    mainAxisSize: MainAxisSize.min,
    children: [
      _LanguageLabel(label: label),
      const SizedBox(height: 1),
      Container(
        constraints: const BoxConstraints(minHeight: 48),
        width: double.infinity,
        alignment: Alignment.centerLeft,
        padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 10),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          border: Border.all(
            color: Theme.of(context).colorScheme.outlineVariant,
          ),
          borderRadius: BorderRadius.circular(11),
        ),
        child: Text(
          value,

          style: TextStyle(
            color: Theme.of(context).colorScheme.onSurface,
            fontSize: 15,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
    ],
  );
}
