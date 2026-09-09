import 'package:prana_mobile/l10n/app_localizations.dart';
import 'package:prana_mobile/app/di/radio_providers.dart';
import 'package:prana_mobile/domain/radio/results.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

class TranslationResultCard extends ConsumerWidget {
  const TranslationResultCard({
    super.key,
    required this.result,
    this.showPlayback = true,
  });

  final TranslationResult result;
  final bool showPlayback;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final speech = ref.watch(translationSpeechProvider);
    final speaking = speech.speakingRequestId == result.requestId;
    final canSpeak =
        (result.translation.trim().isNotEmpty ||
            result.transcript.trim().isNotEmpty) &&
        !(result.error?.trim().isNotEmpty ?? false);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    '${DateFormat.Hms().format(result.timestamp.toLocal())}  ·  '
                    '${result.language.toUpperCase().isEmpty ? '?' : result.language.toUpperCase()}  ·  '
                    '${(result.confidence * 100).round()}%',
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                if (showPlayback)
                  IconButton(
                    key: ValueKey('speak-${result.requestId}'),
                    tooltip:
                        (speaking
                            ? AppLocalizations.of(context).stopSpeaking
                            : AppLocalizations.of(context).speakTranslation),
                    visualDensity: VisualDensity.compact,
                    constraints: const BoxConstraints(
                      minWidth: 48,
                      minHeight: 48,
                    ),
                    padding: EdgeInsets.zero,
                    onPressed:
                        canSpeak
                            ? () {
                              if (speaking) {
                                speech.stopCurrent();
                              } else {
                                speech.speakNow(result);
                              }
                            }
                            : null,
                    iconSize: 20,
                    icon: Icon(
                      speaking
                          ? Icons.stop_circle_outlined
                          : Icons.volume_up_outlined,
                    ),
                  ),
              ],
            ),
            if (result.error != null) ...[
              const SizedBox(height: 10),
              Text(
                result.error!,
                style: const TextStyle(color: Color(0xFFB12F40)),
              ),
            ],
            if (result.transcript.isNotEmpty) ...[
              const SizedBox(height: 10),
              Text(
                result.transcript,
                style: const TextStyle(fontSize: 14, color: Color(0xFF355762)),
              ),
            ],
            if (result.translation.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(
                result.translation,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurface,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
