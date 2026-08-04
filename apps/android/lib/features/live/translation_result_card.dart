import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/localization.dart';
import '../../core/theme.dart';
import '../../models/station.dart';
import '../../providers.dart';

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
                    style: const TextStyle(
                      color: PranaTheme.muted,
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                if (showPlayback)
                  IconButton(
                    key: ValueKey('speak-${result.requestId}'),
                    tooltip: AppText.of(
                      context,
                      speaking ? 'stop_speaking' : 'speak_translation',
                    ),
                    visualDensity: VisualDensity.compact,
                    constraints: const BoxConstraints(
                      minWidth: 32,
                      minHeight: 32,
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
                  color: PranaTheme.navy,
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
