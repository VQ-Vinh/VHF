part of '../live_screen.dart';

class LiveFeedHeader extends ConsumerWidget {
  const LiveFeedHeader({super.key, required this.onHistory});
  final VoidCallback onHistory;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final speech = ref.watch(translationSpeechProvider);
    final audioEnabled = speech.autoPlaybackEnabled;
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 11, 10, 5),
      child: Row(
        children: [
          Expanded(
            child: Text(
              AppLocalizations.of(context).translations.toUpperCase(),
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w800,
                letterSpacing: .8,
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ),
          IconButton(
            key: const ValueKey('live-audio-toggle'),
            tooltip:
                (audioEnabled
                    ? AppLocalizations.of(context).disableLiveAudio
                    : AppLocalizations.of(context).enableLiveAudio),
            isSelected: audioEnabled,
            onPressed: () => speech.setAutoPlaybackEnabled(!audioEnabled),
            icon: Icon(
              audioEnabled
                  ? Icons.volume_up_outlined
                  : Icons.volume_off_outlined,
              color:
                  audioEnabled
                      ? Theme.of(context).colorScheme.primary
                      : Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
          IconButton(
            key: const ValueKey('live-history-button'),
            constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
            tooltip: AppLocalizations.of(context).history,
            onPressed: onHistory,
            icon: const Icon(Icons.history, color: PranaTheme.brandBlue),
          ),
        ],
      ),
    );
  }
}

/// Shows only the newest translation of the day. Everything older stays one tap
/// away behind the history button in [LiveFeedHeader].
class _TranslationFeed extends StatelessWidget {
  const _TranslationFeed({required this.value, required this.onRetry});
  final AsyncValue<List<TranslationResult>> value;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => value.when(
    loading: () => const _ResultSkeleton(),
    error:
        (error, _) => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(
                  Icons.cloud_off,
                  size: 52,
                  color: PranaTheme.brandBlue,
                ),
                const SizedBox(height: 16),
                Text(
                  AppLocalizations.of(context).realtimeError,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  localizedServiceMessage(
                    context,
                    error is PranaApiFailure
                        ? error.messageKey
                        : 'error_api_unreachable',
                  ),
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                ),
                const SizedBox(height: 18),
                FilledButton.icon(
                  key: const ValueKey('live-results-retry'),
                  onPressed: onRetry,
                  icon: const Icon(Icons.refresh),
                  label: Text(AppLocalizations.of(context).retry),
                ),
              ],
            ),
          ),
        ),
    data: (items) {
      if (items.isEmpty) {
        return EmptyState(
          icon: Icons.graphic_eq,
          title: AppLocalizations.of(context).emptyTitle,
          subtitle: AppLocalizations.of(context).emptyBody,
        );
      }
      final newest = items.last;
      // Scrollable so a long translation still fits without overflowing, but
      // shrink-wrapped so a short one leaves the space to the talk button.
      return Padding(
        padding: const EdgeInsets.fromLTRB(16, 6, 16, 12),
        child: TranslationResultCard(
          key: ValueKey(newest.requestId),
          result: newest,
        ),
      );
    },
  );
}

class _QuotaBanner extends StatelessWidget {
  const _QuotaBanner({required this.account});
  final AsyncValue<Map<String, dynamic>> account;

  @override
  Widget build(BuildContext context) => account.maybeWhen(
    data: (data) {
      final usage = Map<String, dynamic>.from(
        data['usage'] as Map? ?? const {},
      );
      final used = (usage['used_audio_seconds'] as num?)?.toDouble() ?? 0;
      final limit = (usage['audio_seconds_limit'] as num?)?.toDouble() ?? 0;
      if (limit <= 0 || used / limit < .9) return const SizedBox.shrink();
      final exhausted = used >= limit;
      return Container(
        width: double.infinity,
        color: exhausted ? const Color(0xFFF9E1E5) : const Color(0xFFFFF3D8),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 9),
        child: Text(
          (exhausted
              ? AppLocalizations.of(context).quotaExhausted
              : AppLocalizations.of(context).quotaNear),
          style: TextStyle(
            color:
                exhausted ? const Color(0xFFA42A3A) : const Color(0xFF6D4A00),
            fontWeight: FontWeight.w700,
          ),
        ),
      );
    },
    orElse: () => const SizedBox.shrink(),
  );
}

class _CommandErrorBanner extends StatelessWidget {
  const _CommandErrorBanner({
    required this.error,
    required this.onDismiss,
    this.actionLabel,
    this.onAction,
    this.secondaryActionLabel,
    this.onSecondaryAction,
    this.showDismiss = true,
  });
  final String error;
  final VoidCallback onDismiss;
  final String? actionLabel;
  final VoidCallback? onAction;
  final String? secondaryActionLabel;
  final VoidCallback? onSecondaryAction;
  final bool showDismiss;

  @override
  Widget build(BuildContext context) => MaterialBanner(
    content: Text(error),
    leading: const Icon(Icons.error_outline, color: Color(0xFFB12F40)),
    actions: [
      if (actionLabel != null && onAction != null)
        TextButton(onPressed: onAction, child: Text(actionLabel!)),
      if (secondaryActionLabel != null && onSecondaryAction != null)
        TextButton(
          onPressed: onSecondaryAction,
          child: Text(secondaryActionLabel!),
        ),
      if (showDismiss)
        TextButton(onPressed: onDismiss, child: const Text('OK')),
    ],
  );
}

class _RetryingBanner extends StatelessWidget {
  const _RetryingBanner({required this.attempt});
  final int attempt;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    color: const Color(0xFFFFF3D8),
    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
    child: Row(
      children: [
        const SizedBox(
          width: 18,
          height: 18,
          child: CircularProgressIndicator(
            strokeWidth: 2,
            color: Color(0xFF9A6700),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Text(
            AppLocalizations.of(context).processingRetrying('$attempt'),
            style: const TextStyle(
              color: Color(0xFF6D4A00),
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
      ],
    ),
  );
}

class _ResultSkeleton extends StatelessWidget {
  const _ResultSkeleton();
  @override
  Widget build(BuildContext context) => const Padding(
    padding: EdgeInsets.fromLTRB(16, 6, 16, 12),
    child: Align(
      alignment: Alignment.topCenter,
      child: Card(child: SizedBox(height: 116, width: double.infinity)),
    ),
  );
}
