import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:prana_mobile/core/localization.dart';
import 'package:prana_mobile/l10n/app_localizations.dart';

class LanguageSetting extends StatelessWidget {
  const LanguageSetting({
    super.key,
    required this.country,
    required this.value,
    required this.onChanged,
  });
  final String? country;
  final String value;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final choices = CountryLocalePolicy.choices(country);
    final theme = Theme.of(context);
    final labelStyle = theme.textTheme.bodyMedium!;
    final optionStyle = theme.textTheme.labelLarge!.copyWith(
      fontWeight: FontWeight.w700,
    );
    double measure(String text, TextStyle style) {
      final painter = TextPainter(
        text: TextSpan(text: text, style: style),
        textDirection: Directionality.of(context),
        textScaler: MediaQuery.textScalerOf(context),
      )..layout();
      final width = painter.width;
      painter.dispose();
      return width;
    }

    final toggleWidth = choices.fold<double>(
      6,
      (width, locale) =>
          width +
          math.max(
            48,
            measure(locale.languageCode.toUpperCase(), optionStyle) + 16,
          ),
    );
    final toggle = Container(
      key: const ValueKey('interface-language-toggle'),
      padding: const EdgeInsets.all(2),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(99),
        border: Border.all(color: theme.colorScheme.outlineVariant),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          for (final locale in choices)
            Semantics(
              selected: value == locale.languageCode,
              button: true,
              child: Material(
                color:
                    value == locale.languageCode
                        ? theme.colorScheme.secondaryContainer
                        : Colors.transparent,
                borderRadius: BorderRadius.circular(99),
                child: InkWell(
                  key: ValueKey('interface-language-${locale.languageCode}'),
                  borderRadius: BorderRadius.circular(99),
                  onTap: () => onChanged(locale.languageCode),
                  child: Container(
                    constraints: const BoxConstraints(
                      minWidth: 48,
                      minHeight: 48,
                    ),
                    padding: const EdgeInsets.all(8),
                    alignment: Alignment.center,
                    child: Text(
                      locale.languageCode.toUpperCase(),
                      style: optionStyle,
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        LayoutBuilder(
          builder: (context, constraints) {
            final fits =
                measure(l10n.uiLanguage, labelStyle) + 16 + toggleWidth <=
                constraints.maxWidth;
            if (fits) {
              return Row(
                children: [
                  Expanded(child: Text(l10n.uiLanguage, style: labelStyle)),
                  const SizedBox(width: 16),
                  toggle,
                ],
              );
            }
            return Wrap(
              alignment: WrapAlignment.end,
              runSpacing: 8,
              children: [
                SizedBox(
                  width: constraints.maxWidth,
                  child: Text(l10n.uiLanguage, style: labelStyle),
                ),
                toggle,
              ],
            );
          },
        ),
        if (country != null && country!.isNotEmpty && choices.length == 1) ...[
          const SizedBox(height: 8),
          Text(
            l10n.countryLanguageUnavailable,
            style: theme.textTheme.bodySmall,
          ),
        ],
      ],
    );
  }
}
