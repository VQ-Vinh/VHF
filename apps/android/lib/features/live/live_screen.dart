import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/localization.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../../models/station.dart';
import '../../providers.dart';
import '../history/history_screen.dart';
import 'live_controller.dart';

class LiveScreen extends ConsumerStatefulWidget {
  const LiveScreen({super.key, required this.stationId});
  final String stationId;

  static const languages = {
    'vi': 'Tiếng Việt',
    'en': 'English',
    'zh': '中文',
    'ja': '日本語',
    'ko': '한국어',
  };

  @override
  ConsumerState<LiveScreen> createState() => _LiveScreenState();
}

class _LiveScreenState extends ConsumerState<LiveScreen> {
  String? _dismissedProcessingError;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      ref.read(activeSpeechStationProvider.notifier).state = widget.stationId;
    });
  }

  Future<void> _showHistory() async {
    final wide = MediaQuery.sizeOf(context).width >= 700;
    if (wide) {
      await showDialog<void>(
        context: context,
        builder:
            (context) => Dialog(
              child: SizedBox(
                width: 680,
                height: 720,
                child: HistoryScreen(
                  stationId: widget.stationId,
                  embedded: true,
                ),
              ),
            ),
      );
    } else {
      await showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        useSafeArea: true,
        builder:
            (context) => FractionallySizedBox(
              heightFactor: .94,
              child: HistoryScreen(stationId: widget.stationId, embedded: true),
            ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final stationValue = ref.watch(stationProvider(widget.stationId));
    final now = ref.watch(stationClockProvider).value ?? DateTime.now();
    final apiOnline = ref.watch(apiHealthProvider).value ?? false;
    return stationValue.when(
      loading:
          () =>
              const Scaffold(body: Center(child: CircularProgressIndicator())),
      error:
          (error, _) =>
              Scaffold(appBar: AppBar(), body: Center(child: Text('$error'))),
      data: (station) {
        if (station == null) {
          return Scaffold(
            body: EmptyState(
              icon: Icons.radio,
              title: AppText.of(context, 'station_missing'),
            ),
          );
        }

        final online = station.isOnlineAt(now);
        final controller = ref.watch(
          liveUxControllerProvider(widget.stationId),
        );
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (mounted) controller.synchronize(station, online: online);
        });
        final ux = controller.state;
        final entitlements = ref.watch(planEntitlementsProvider);
        final results = ref.watch(
          liveResultsProvider((
            stationId: widget.stationId,
            sessionId: station.sessionId,
          )),
        );
        final items = results.value ?? const <TranslationResult>[];
        final detectedLanguage =
            items.isEmpty || items.first.language.isEmpty
                ? null
                : items.first.language;
        final targetLanguage =
            ux.optimisticLanguage ?? station.desired.targetLanguage;
        final processingErrorKey =
            '${station.lastError ?? ''}|${station.sequence}';
        final showProcessingError =
            !station.retrying &&
            (station.lastError?.isNotEmpty ?? false) &&
            _dismissedProcessingError != processingErrorKey;

        return Scaffold(
          appBar: LiveHeader(
            station: station,
            online: online,
            ux: ux,
            onToggle:
                online && !ux.busy && !station.commandPending
                    ? () =>
                        controller.setRunning(station, !station.desired.running)
                    : null,
            onSettings:
                () => context.push('/stations/${widget.stationId}/settings'),
          ),
          body: Column(
            children: [
              LanguageStrip(
                detectedLanguage: detectedLanguage,
                targetLanguage: targetLanguage,
                enabled: online && !ux.busy,
                onChanged: (value) => controller.setLanguage(station, value),
              ),
              _QuotaBanner(account: ref.watch(accountProvider)),
              if (station.retrying)
                _RetryingBanner(attempt: station.retryAttempt),
              if (ux.error != null)
                _CommandErrorBanner(
                  error: AppText.of(context, ux.error!),
                  onDismiss: controller.dismissError,
                ),
              if (showProcessingError)
                _CommandErrorBanner(
                  error: AppText.of(context, station.lastError!),
                  onDismiss:
                      () => setState(
                        () => _dismissedProcessingError = processingErrorKey,
                      ),
                  actionLabel: AppText.of(context, 'retry'),
                  onAction:
                      online && !ux.busy && !station.retrying
                          ? () => controller.retry(station)
                          : null,
                ),
              _FeedHeader(
                onHistory: _showHistory,
                count: items.length,
                limit: entitlements.liveLogLimit,
              ),
              Expanded(child: _TranslationFeed(value: results)),
              _BottomStatus(
                station: station,
                online: online,
                apiOnline: apiOnline,
                ux: ux,
              ),
            ],
          ),
        );
      },
    );
  }
}

class LiveHeader extends StatelessWidget implements PreferredSizeWidget {
  const LiveHeader({
    super.key,
    required this.station,
    required this.online,
    required this.ux,
    required this.onToggle,
    required this.onSettings,
  });

  final StationModel station;
  final bool online;
  final LiveUxState ux;
  final VoidCallback? onToggle;
  final VoidCallback onSettings;

  @override
  Size get preferredSize => const Size.fromHeight(76);

  @override
  Widget build(BuildContext context) {
    final running = station.desired.running;
    final waiting = ux.busy || station.commandPending;
    return AppBar(
      key: const ValueKey('live-header'),
      toolbarHeight: 76,
      leadingWidth: 48,
      titleSpacing: 0,
      title: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            station.name,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 4),
          _RxBadge(station: station, online: online),
        ],
      ),
      actions: [
        IconButton(
          tooltip: AppText.of(context, 'station_settings'),
          onPressed: onSettings,
          constraints: const BoxConstraints.tightFor(width: 44, height: 44),
          padding: const EdgeInsets.all(10),
          icon: const Icon(Icons.settings_outlined),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 16),
          child: FilledButton.icon(
            style: FilledButton.styleFrom(
              minimumSize: const Size(88, 40),
              backgroundColor:
                  running ? const Color(0xFFF4B942) : PranaTheme.brandBlue,
              foregroundColor: running ? const Color(0xFF2D2106) : Colors.white,
              padding: const EdgeInsets.symmetric(horizontal: 8),
            ),
            onPressed: onToggle,
            icon:
                waiting
                    ? const SizedBox(
                      width: 15,
                      height: 15,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                    : Icon(running ? Icons.stop : Icons.play_arrow, size: 17),
            label: Text(
              waiting
                  ? AppText.of(context, 'waiting')
                  : AppText.of(context, running ? 'stop' : 'start'),
              maxLines: 1,
            ),
          ),
        ),
        const SizedBox(width: 4),
      ],
    );
  }
}

class _RxBadge extends StatelessWidget {
  const _RxBadge({required this.station, required this.online});
  final StationModel station;
  final bool online;

  @override
  Widget build(BuildContext context) {
    final state = online ? station.captureState.toUpperCase() : 'OFF';
    final active = online && station.captureState != 'idle';
    return Container(
      constraints: const BoxConstraints(minWidth: 62),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: active ? PranaTheme.brandBlue : const Color(0xFF173B63),
        border: Border.all(
          color: active ? PranaTheme.brandBlueBright : const Color(0xFF52769B),
        ),
        borderRadius: BorderRadius.circular(7),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.circle,
            size: 7,
            color: online ? const Color(0xFF6DE2D1) : const Color(0xFFA9C5CC),
          ),
          const SizedBox(width: 5),
          Text(
            'RX $state',
            style: const TextStyle(
              color: Colors.white,
              fontSize: 10,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}

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
    color: PranaTheme.brandBlueSoft,
    padding: const EdgeInsets.fromLTRB(12, 10, 12, 12),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Expanded(
          child: _LanguageValue(
            key: const ValueKey('input-language-field'),
            label: AppText.of(context, 'input'),
            value:
                detectedLanguage == null
                    ? AppText.of(context, 'detecting')
                    : LiveScreen.languages[detectedLanguage] ??
                        detectedLanguage!.toUpperCase(),
          ),
        ),
        const SizedBox(
          width: 36,
          height: 50,
          child: Icon(Icons.arrow_forward, color: PranaTheme.brandBlue),
        ),
        Expanded(
          child: Column(
            key: const ValueKey('output-language-field'),
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              _LanguageLabel(label: AppText.of(context, 'output')),
              const SizedBox(height: 6),
              SizedBox(
                height: 50,
                child: DropdownButtonFormField<String>(
                  key: ValueKey(targetLanguage),
                  initialValue:
                      LiveScreen.languages.containsKey(targetLanguage)
                          ? targetLanguage
                          : 'en',
                  isExpanded: true,
                  decoration: const InputDecoration(
                    isDense: true,
                    contentPadding: EdgeInsets.symmetric(
                      horizontal: 13,
                      vertical: 12,
                    ),
                  ),
                  items:
                      LiveScreen.languages.entries
                          .map(
                            (entry) => DropdownMenuItem(
                              value: entry.key,
                              child: Text(
                                entry.value,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
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
    maxLines: 1,
    overflow: TextOverflow.ellipsis,
    style: const TextStyle(
      color: PranaTheme.muted,
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
      const SizedBox(height: 6),
      Container(
        height: 50,
        width: double.infinity,
        alignment: Alignment.centerLeft,
        padding: const EdgeInsets.symmetric(horizontal: 13),
        decoration: BoxDecoration(
          color: PranaTheme.surface,
          border: Border.all(color: const Color(0xFFB9CDD2)),
          borderRadius: BorderRadius.circular(11),
        ),
        child: Text(
          value,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(
            color: PranaTheme.navy,
            fontSize: 16,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
    ],
  );
}

class _FeedHeader extends StatelessWidget {
  const _FeedHeader({
    required this.onHistory,
    required this.count,
    required this.limit,
  });
  final VoidCallback onHistory;
  final int count;
  final int limit;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(16, 11, 10, 5),
    child: Row(
      children: [
        Text(
          AppText.of(context, 'translations').toUpperCase(),
          style: const TextStyle(
            fontSize: 10,
            fontWeight: FontWeight.w800,
            letterSpacing: .8,
            color: PranaTheme.muted,
          ),
        ),
        if (limit > 0) ...[
          const SizedBox(width: 10),
          Tooltip(
            message: AppText.format(context, 'live_log_usage', {
              'count': count,
              'limit': limit,
            }),
            child: Text(
              '$count/$limit',
              style: const TextStyle(fontSize: 10, color: PranaTheme.muted),
            ),
          ),
        ],
        const Spacer(),
        IconButton(
          tooltip: AppText.of(context, 'history'),
          onPressed: onHistory,
          icon: const Icon(Icons.history, color: PranaTheme.brandBlue),
        ),
      ],
    ),
  );
}

class _TranslationFeed extends StatefulWidget {
  const _TranslationFeed({required this.value});
  final AsyncValue<List<TranslationResult>> value;

  @override
  State<_TranslationFeed> createState() => _TranslationFeedState();
}

class _TranslationFeedState extends State<_TranslationFeed> {
  final _scrollController = ScrollController();
  String? _visibleResultSignature;

  void _scrollToNewest({required bool animate}) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollController.hasClients) return;
      final target = _scrollController.position.maxScrollExtent;
      if (animate) {
        _scrollController.animateTo(
          target,
          duration: const Duration(milliseconds: 240),
          curve: Curves.easeOut,
        );
      } else {
        _scrollController.jumpTo(target);
      }
    });
  }

  @override
  void didUpdateWidget(covariant _TranslationFeed oldWidget) {
    super.didUpdateWidget(oldWidget);
    final items = widget.value.value ?? const <TranslationResult>[];
    final signature = items.map((item) => item.requestId).join('|');
    final hasNewResult =
        signature.isNotEmpty && signature != _visibleResultSignature;
    final nearNewest =
        !_scrollController.hasClients ||
        _scrollController.position.maxScrollExtent -
                _scrollController.position.pixels <=
            80;
    if (hasNewResult && nearNewest) {
      _scrollToNewest(animate: _visibleResultSignature != null);
    }
    _visibleResultSignature = signature;
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => widget.value.when(
    loading: () => const _ResultSkeleton(),
    error:
        (error, _) => EmptyState(
          icon: Icons.cloud_off,
          title: AppText.of(context, 'realtime_error'),
          subtitle: '$error',
        ),
    data: (items) {
      if (items.isNotEmpty && _visibleResultSignature == null) {
        _visibleResultSignature = items.map((item) => item.requestId).join('|');
        _scrollToNewest(animate: false);
      }
      return items.isEmpty
          ? EmptyState(
            icon: Icons.graphic_eq,
            title: AppText.of(context, 'empty_title'),
            subtitle: AppText.of(context, 'empty_body'),
          )
          : ListView.separated(
            controller: _scrollController,
            padding: const EdgeInsets.fromLTRB(16, 6, 16, 18),
            itemCount: items.length,
            separatorBuilder: (_, _) => const SizedBox(height: 10),
            itemBuilder:
                (_, index) => _ResultCard(
                  key: ValueKey(items[index].requestId),
                  result: items[index],
                ),
          );
    },
  );
}

class _ResultCard extends ConsumerWidget {
  const _ResultCard({super.key, required this.result});
  final TranslationResult result;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final speech = ref.watch(translationSpeechProvider);
    final speaking = speech.speakingRequestId == result.requestId;
    final canSpeak =
        result.translation.trim().isNotEmpty &&
        !(result.error?.trim().isNotEmpty ?? false);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '${DateFormat.Hms().format(result.timestamp)}  ·  '
              '${result.language.toUpperCase().isEmpty ? '?' : result.language.toUpperCase()}  ·  '
              '${(result.confidence * 100).round()}%',
              style: const TextStyle(
                color: PranaTheme.muted,
                fontSize: 10,
                fontWeight: FontWeight.w700,
              ),
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
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Text(
                      result.translation,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: PranaTheme.navy,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton(
                    key: ValueKey('speak-${result.requestId}'),
                    tooltip: AppText.of(
                      context,
                      speaking ? 'stop_speaking' : 'speak_translation',
                    ),
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
                    icon: Icon(
                      speaking
                          ? Icons.stop_circle_outlined
                          : Icons.volume_up_outlined,
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _BottomStatus extends StatelessWidget {
  const _BottomStatus({
    required this.station,
    required this.online,
    required this.apiOnline,
    required this.ux,
  });
  final StationModel station;
  final bool online;
  final bool apiOnline;
  final LiveUxState ux;

  @override
  Widget build(BuildContext context) {
    final pipeline = online ? station.captureState.toUpperCase() : 'OFFLINE';
    final apiOk = apiOnline;
    return Container(
      height: 36,
      color: const Color(0xFFDCE9ED),
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          _StatusDot(label: pipeline, ok: online),
          const Spacer(),
          _StatusDot(
            label: apiOk ? AppText.of(context, 'api_ready') : 'API OFFLINE',
            ok: apiOk,
          ),
        ],
      ),
    );
  }
}

class _StatusDot extends StatelessWidget {
  const _StatusDot({required this.label, required this.ok});
  final String label;
  final bool ok;
  @override
  Widget build(BuildContext context) => Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      Icon(
        Icons.circle,
        size: 7,
        color: ok ? const Color(0xFF21835A) : const Color(0xFFC34655),
      ),
      const SizedBox(width: 6),
      Text(
        label,
        style: const TextStyle(
          fontSize: 10,
          fontWeight: FontWeight.w800,
          color: Color(0xFF355762),
        ),
      ),
    ],
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
          AppText.of(context, exhausted ? 'quota_exhausted' : 'quota_near'),
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
  });
  final String error;
  final VoidCallback onDismiss;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) => MaterialBanner(
    content: Text(error),
    leading: const Icon(Icons.error_outline, color: Color(0xFFB12F40)),
    actions: [
      if (actionLabel != null && onAction != null)
        TextButton(onPressed: onAction, child: Text(actionLabel!)),
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
            AppText.format(context, 'processing_retrying', {
              'attempt': '$attempt',
            }),
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
  Widget build(BuildContext context) => ListView.builder(
    padding: const EdgeInsets.all(16),
    itemCount: 4,
    itemBuilder: (_, _) => const Card(child: SizedBox(height: 116)),
  );
}
