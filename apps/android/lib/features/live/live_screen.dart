import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/localization.dart';
import '../../core/languages.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../../models/station.dart';
import '../../providers.dart';
import '../history/history_screen.dart';
import 'translation_result_card.dart';
import '../tx/application/fake_tx_repository.dart';
import '../tx/application/tx_controller.dart';
import '../tx/domain/tx_phase.dart';
import '../tx/presentation/widgets/tx_live_dock.dart';
import '../tx/presentation/widgets/tx_review_card.dart';
import 'live_controller.dart';

class LiveScreen extends ConsumerStatefulWidget {
  const LiveScreen({super.key, required this.stationId});
  final String stationId;

  @override
  ConsumerState<LiveScreen> createState() => _LiveScreenState();
}

class _LiveScreenState extends ConsumerState<LiveScreen> {
  String? _dismissedProcessingError;
  late final TxController _txController;
  bool _requiresDiscardConfirmation = false;
  bool _reviewOpen = false;

  @override
  void initState() {
    super.initState();
    _txController = TxController(
      stationId: widget.stationId,
      repository: FakeTxRepository(),
    );
    _txController.addListener(_onTxChanged);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      ref.read(activeSpeechStationProvider.notifier).state = widget.stationId;
    });
  }

  void _onTxChanged() {
    final requiresDiscard = _txController.state.requiresLeaveConfirmation;
    if (requiresDiscard != _requiresDiscardConfirmation && mounted) {
      setState(() => _requiresDiscardConfirmation = requiresDiscard);
    }
    if (_txController.state.phase == TxPhase.reviewReady && !_reviewOpen) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _showTxReview();
      });
    }
  }

  Future<void> _showTxReview() async {
    final draft = _txController.state.draft;
    if (_reviewOpen ||
        draft == null ||
        _txController.state.phase != TxPhase.reviewReady) {
      return;
    }
    _reviewOpen = true;
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder:
          (sheetContext) => FractionallySizedBox(
            heightFactor: .72,
            child: TxReviewCard(
              draft: draft,
              languageLabel:
                  supportedLanguages[draft.targetLanguage] ??
                  draft.targetLanguage.toUpperCase(),
              onTransmit: () {
                Navigator.pop(sheetContext);
                _txController.confirmTransmission();
              },
              onCancel: () {
                Navigator.pop(sheetContext);
                _txController.cancelDraft();
              },
            ),
          ),
    );
    _reviewOpen = false;
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
          if (!mounted) return;
          controller.synchronize(station, online: online);
          _txController.setStationOnline(online);
        });
        final ux = controller.state;
        final stationDisplayState = liveStationDisplayState(
          station: station,
          online: online,
          ux: ux,
        );
        final entitlements = ref.watch(planEntitlementsProvider);
        final results = ref.watch(
          liveResultsProvider((
            stationId: widget.stationId,
            localDate: localDateKey(now),
            timezoneOffsetMinutes: now.timeZoneOffset.inMinutes,
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

        final body = Column(
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
            LiveFeedHeader(
              onHistory: _showHistory,
              count: items.length,
              limit: entitlements.liveLogLimit,
            ),
            Expanded(child: _TranslationFeed(value: results)),
            TxLiveDock(
              controller: _txController,
              stationState: stationDisplayState,
              stationOnline: online,
              apiOnline: apiOnline,
              onReview: _showTxReview,
            ),
          ],
        );
        return PopScope(
          canPop: !_requiresDiscardConfirmation,
          onPopInvokedWithResult: (didPop, _) async {
            if (didPop) return;
            final discard = await showDialog<bool>(
              context: context,
              builder:
                  (context) => AlertDialog(
                    title: Text(AppText.of(context, 'tx_discard_title')),
                    content: Text(AppText.of(context, 'tx_discard_body')),
                    actions: [
                      TextButton(
                        onPressed: () => Navigator.pop(context, false),
                        child: Text(AppText.of(context, 'close')),
                      ),
                      FilledButton(
                        onPressed: () => Navigator.pop(context, true),
                        child: Text(AppText.of(context, 'tx_discard')),
                      ),
                    ],
                  ),
            );
            if (discard == true && context.mounted) {
              await _txController.cancelDraft();
              if (context.mounted) context.pop();
            }
          },
          child: Scaffold(
            appBar: LiveHeader(
              station: station,
              online: online,
              ux: ux,
              txController: _txController,
              onToggle:
                  online && !ux.busy && !station.commandPending
                      ? () => controller.setRunning(
                        station,
                        !station.desired.running,
                      )
                      : null,
              onSettings:
                  () => context.push('/stations/${widget.stationId}/settings'),
            ),
            body: body,
          ),
        );
      },
    );
  }

  @override
  void dispose() {
    _txController.removeListener(_onTxChanged);
    _txController.dispose();
    super.dispose();
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
    this.txController,
  });

  final StationModel station;
  final bool online;
  final LiveUxState ux;
  final VoidCallback? onToggle;
  final VoidCallback onSettings;
  final TxController? txController;

  @override
  Size get preferredSize => const Size.fromHeight(64);

  @override
  Widget build(BuildContext context) {
    final running = station.desired.running;
    final waiting = ux.busy || station.commandPending;
    final transitionRunning = ux.pendingRunning ?? station.desired.running;
    final buttonRunning = waiting ? transitionRunning : running;
    final stationDisplayState = liveStationDisplayState(
      station: station,
      online: online,
      ux: ux,
    );
    return AppBar(
      key: const ValueKey('live-header'),
      toolbarHeight: 64,
      leadingWidth: 44,
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
          const SizedBox(height: 2),
          if (txController == null)
            _RxBadge(stationState: stationDisplayState, online: online)
          else
            AnimatedBuilder(
              animation: txController!,
              builder:
                  (context, _) => _RxBadge(
                    stationState: stationDisplayState,
                    online: online,
                    txActive:
                        txController!.state.phase == TxPhase.recording ||
                        txController!.state.phase == TxPhase.transmitting,
                  ),
            ),
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
          padding: const EdgeInsets.symmetric(vertical: 10),
          child: Semantics(
            liveRegion: waiting,
            button: true,
            enabled: !waiting && onToggle != null,
            label:
                waiting
                    ? AppText.of(
                      context,
                      transitionRunning ? 'starting' : 'stopping',
                    )
                    : AppText.of(context, running ? 'stop' : 'start'),
            child: Material(
              key: const ValueKey('live-toggle-button'),
              color:
                  buttonRunning
                      ? const Color(0xFFF4B942)
                      : PranaTheme.brandBlue,
              borderRadius: BorderRadius.circular(12),
              clipBehavior: Clip.antiAlias,
              child: InkWell(
                onTap: waiting ? null : onToggle,
                child: SizedBox(
                  width: 118,
                  height: 40,
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      if (waiting)
                        SizedBox(
                          key: const ValueKey('live-toggle-progress'),
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(
                            strokeWidth: 2.6,
                            valueColor: AlwaysStoppedAnimation<Color>(
                              buttonRunning
                                  ? const Color(0xFF2D2106)
                                  : Colors.white,
                            ),
                          ),
                        )
                      else
                        Icon(
                          running ? Icons.stop : Icons.play_arrow,
                          size: 17,
                          color:
                              buttonRunning
                                  ? const Color(0xFF2D2106)
                                  : Colors.white,
                        ),
                      const SizedBox(width: 7),
                      Flexible(
                        child: Text(
                          waiting
                              ? AppText.of(
                                context,
                                transitionRunning ? 'starting' : 'stopping',
                              )
                              : AppText.of(context, running ? 'stop' : 'start'),
                          key: const ValueKey('live-toggle-label'),
                          maxLines: 1,
                          style: TextStyle(
                            color:
                                buttonRunning
                                    ? const Color(0xFF2D2106)
                                    : Colors.white,
                            fontSize: 12,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
        const SizedBox(width: 4),
      ],
    );
  }
}

String liveStationDisplayState({
  required StationModel station,
  required bool online,
  required LiveUxState ux,
}) {
  if (!online) return 'OFF';
  if (ux.busy || station.commandPending) {
    final pendingRunning = ux.pendingRunning ?? station.desired.running;
    return pendingRunning ? 'STARTING' : 'STOPPING';
  }
  return station.captureState.toUpperCase();
}

class _RxBadge extends StatelessWidget {
  const _RxBadge({
    required this.stationState,
    required this.online,
    this.txActive = false,
  });
  final String stationState;
  final bool online;
  final bool txActive;

  @override
  Widget build(BuildContext context) {
    final state = txActive ? 'TX' : stationState;
    final active =
        txActive ||
        state == 'STARTING' ||
        state == 'STOPPING' ||
        online && state != 'IDLE';
    return Container(
      constraints: const BoxConstraints(minWidth: 62),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color:
            txActive
                ? const Color(0xFF9E2637)
                : active
                ? PranaTheme.brandBlue
                : const Color(0xFF173B63),
        border: Border.all(
          color:
              txActive
                  ? const Color(0xFFFF9BA7)
                  : active
                  ? PranaTheme.brandBlueBright
                  : const Color(0xFF52769B),
        ),
        borderRadius: BorderRadius.circular(7),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.circle,
            size: 7,
            color:
                txActive
                    ? const Color(0xFFFFC0C8)
                    : online
                    ? const Color(0xFF6DE2D1)
                    : const Color(0xFFA9C5CC),
          ),
          const SizedBox(width: 5),
          Text(
            txActive ? state : 'RX $state',
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
    key: const ValueKey('rx-language-strip'),
    color: PranaTheme.brandBlueSoft,
    padding: const EdgeInsets.fromLTRB(10, 6, 10, 8),
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
                    : supportedLanguages[detectedLanguage] ??
                        detectedLanguage!.toUpperCase(),
          ),
        ),
        const SizedBox(
          key: ValueKey('rx-language-arrow'),
          width: 32,
          height: 40,
          child: Icon(Icons.arrow_forward, color: PranaTheme.brandBlue),
        ),
        Expanded(
          child: Column(
            key: const ValueKey('output-language-field'),
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              _LanguageLabel(label: AppText.of(context, 'output')),
              const SizedBox(height: 1),
              SizedBox(
                height: 40,
                child: DropdownButtonFormField<String>(
                  key: ValueKey(targetLanguage),
                  initialValue:
                      supportedLanguages.containsKey(targetLanguage)
                          ? targetLanguage
                          : 'en',
                  isExpanded: true,
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
      const SizedBox(height: 1),
      Container(
        height: 40,
        width: double.infinity,
        alignment: Alignment.centerLeft,
        padding: const EdgeInsets.symmetric(horizontal: 11),
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
            fontSize: 15,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
    ],
  );
}

class LiveFeedHeader extends ConsumerWidget {
  const LiveFeedHeader({
    super.key,
    required this.onHistory,
    required this.count,
    required this.limit,
  });
  final VoidCallback onHistory;
  final int count;
  final int limit;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final speech = ref.watch(translationSpeechProvider);
    final audioEnabled = speech.autoPlaybackEnabled;
    return Padding(
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
            key: const ValueKey('live-audio-toggle'),
            tooltip: AppText.of(
              context,
              audioEnabled ? 'disable_live_audio' : 'enable_live_audio',
            ),
            isSelected: audioEnabled,
            onPressed: () => speech.setAutoPlaybackEnabled(!audioEnabled),
            icon: Icon(
              audioEnabled
                  ? Icons.volume_up_outlined
                  : Icons.volume_off_outlined,
              color: audioEnabled ? PranaTheme.brandBlue : PranaTheme.muted,
            ),
          ),
          IconButton(
            tooltip: AppText.of(context, 'history'),
            onPressed: onHistory,
            icon: const Icon(Icons.history, color: PranaTheme.brandBlue),
          ),
        ],
      ),
    );
  }
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
                (_, index) => TranslationResultCard(
                  key: ValueKey(items[index].requestId),
                  result: items[index],
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
