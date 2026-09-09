import 'package:prana_mobile/core/service_messages.dart';
import 'package:prana_mobile/l10n/app_localizations.dart';
import 'package:prana_mobile/core/responsive.dart';
import 'package:prana_mobile/app/di/account_providers.dart';
import 'package:prana_mobile/app/di/radio_providers.dart';
import 'package:prana_mobile/app/di/station_providers.dart';
import 'package:prana_mobile/app/di/auth_providers.dart';
import 'package:prana_mobile/domain/radio/results.dart';
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:prana_mobile/core/languages.dart';
import 'package:prana_mobile/core/theme.dart';
import 'package:prana_mobile/core/widgets.dart';
import 'package:prana_mobile/domain/station/station.dart';
import 'package:prana_mobile/data/network/prana_api.dart';
import 'package:prana_mobile/features/station/shared/widgets/translation_result_card.dart';
import 'package:prana_mobile/runtime/vhf/tx_controller.dart';
import 'package:prana_mobile/domain/radio/tx/tx_phase.dart';
import 'package:prana_mobile/features/station/radio/presentation/widgets/tx/tx_live_dock.dart';
import 'package:prana_mobile/features/station/radio/presentation/widgets/tx/tx_review_card.dart';
import 'package:prana_mobile/runtime/vhf/live_controller.dart';

part 'widgets/live_feed.dart';
part 'widgets/language_strip.dart';
part 'widgets/live_header.dart';

class LiveScreen extends ConsumerStatefulWidget {
  const LiveScreen({
    super.key,
    required this.stationId,
    this.active = true,
    this.embedded = false,
    this.onHistory,
  });
  final bool active;
  final bool embedded;
  final VoidCallback? onHistory;
  final String stationId;

  @override
  ConsumerState<LiveScreen> createState() => _LiveScreenState();
}

bool canToggleLiveStation({
  required bool online,
  required bool running,
  required bool busy,
  required bool commandPending,
  bool commandFailed = false,
}) =>
    (online || running) &&
    !busy &&
    // An offline Station can never acknowledge the generation, so treating its
    // command as pending would lock the toggle until it comes back.
    (!commandPending || commandFailed || !online);

/// Whether the review sheet may open itself for this draft.
///
/// The memory is keyed on the draft, not on the phase. Keying it on the phase
/// meant leaving reviewReady erased it, so anything that pushed the phase back
/// -- a restore landing mid-confirm -- reopened the sheet over an edit the user
/// had already sent. The REVIEW button stays the deliberate way back in.
bool shouldAutoOpenTxReview({
  required TxPhase phase,
  required String? draftId,
  required String? autoReviewedDraftId,
  required bool reviewOpen,
}) =>
    phase == TxPhase.reviewReady &&
    draftId != null &&
    !reviewOpen &&
    draftId != autoReviewedDraftId;

class _LiveScreenState extends ConsumerState<LiveScreen> {
  String? _dismissedProcessingError;
  late final TxController _txController;
  String? _editedTranslation;
  String? _editingDraftId;
  bool _reviewOpen = false;

  /// Draft the sheet has already been opened for on its own. Without this the
  /// sheet reopens itself: dismissing it by drag, scrim or back leaves the
  /// phase on reviewReady, and the next controller notification re-triggers
  /// the auto-open. The REVIEW button stays the deliberate way back in.
  String? _autoReviewedDraftId;

  @override
  void initState() {
    super.initState();
    _txController = ref.read(stationSessionProvider(widget.stationId)).tx;
    _txController.addListener(_onTxChanged);
    _onTxChanged();
  }

  @override
  void didUpdateWidget(covariant LiveScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.active && !oldWidget.active) _onTxChanged();
  }

  void _onTxChanged() {
    if (!widget.active) return;
    final draftId = _txController.state.draft?.id;
    if (draftId == null) {
      // Recording, cancelling and resetting all clear the draft, so the next
      // one gets its own automatic review.
      _autoReviewedDraftId = null;
      return;
    }
    if (!shouldAutoOpenTxReview(
      phase: _txController.state.phase,
      draftId: draftId,
      autoReviewedDraftId: _autoReviewedDraftId,
      reviewOpen: _reviewOpen,
    )) {
      return;
    }
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted ||
          !widget.active ||
          _reviewOpen ||
          _txController.state.phase != TxPhase.reviewReady ||
          _txController.state.draft?.id != draftId ||
          _autoReviewedDraftId == draftId) {
        return;
      }
      _autoReviewedDraftId = draftId;
      _showTxReview();
    });
  }

  @override
  void dispose() {
    _txController.removeListener(_onTxChanged);

    super.dispose();
  }

  Future<void> _showTxReview() async {
    final draft = _txController.state.draft;
    if (_reviewOpen ||
        draft == null ||
        _txController.state.phase != TxPhase.reviewReady) {
      return;
    }
    if (_editingDraftId != draft.id) {
      _editingDraftId = draft.id;
      _editedTranslation = draft.translation;
    }
    _reviewOpen = true;
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder:
          (sheetContext) => Padding(
            padding: EdgeInsets.only(
              bottom: MediaQuery.viewInsetsOf(sheetContext).bottom,
            ),
            child: FractionallySizedBox(
              heightFactor: .72,
              child: TxReviewCard(
                draft: draft,
                initialTranslation: _editedTranslation,
                onChanged: (value) => _editedTranslation = value,
                languageLabel:
                    supportedLanguages[draft.targetLanguage] ??
                    draft.targetLanguage.toUpperCase(),
                onTransmit: (translation) {
                  Navigator.pop(sheetContext);
                  _txController.confirmTransmission(translation);
                },
                onCancel: () {
                  Navigator.pop(sheetContext);
                  _txController.cancelDraft();
                },
              ),
            ),
          ),
    );
    _reviewOpen = false;
  }

  void _showHistory() => widget.onHistory?.call();

  @override
  Widget build(BuildContext context) {
    ref.watch(stationSessionProvider(widget.stationId));
    final stationValue = ref.watch(stationProvider(widget.stationId));
    final now = ref.watch(stationClockProvider).value ?? DateTime.now();
    final apiOnline = ref.watch(apiHealthProvider).value ?? false;
    return stationValue.when(
      loading:
          () => const ResponsiveScaffold(
            body: Center(child: CircularProgressIndicator()),
          ),
      error:
          (error, _) => ResponsiveScaffold(
            appBar: ResponsiveHeader(),
            body: Center(child: Text('$error')),
          ),
      data: (station) {
        if (station == null) {
          return ResponsiveScaffold(
            body: EmptyState(
              icon: Icons.radio,
              title: AppLocalizations.of(context).stationMissing,
            ),
          );
        }

        final online = station.isOnlineAt(now);
        final controller = ref.watch(
          liveUxControllerProvider(widget.stationId),
        );
        final ux = controller.state;
        final stationDisplayState = liveStationDisplayState(
          station: station,
          online: online,
          ux: ux,
        );
        final commandFailed =
            station.commandError != null &&
            station.commandFailedGeneration >= station.desired.generation;
        final resultsKey = (
          stationId: widget.stationId,
          localDate: localDateKey(now),
          timezoneOffsetMinutes: now.timeZoneOffset.inMinutes,
          timezone: ref.watch(userRegionProvider).timezoneName,
        );
        final results = ref.watch(liveResultsProvider(resultsKey));
        final items = results.value ?? const <TranslationResult>[];
        // Results arrive oldest first, so the newest one — the only one the
        // feed shows — is the last entry.
        final detectedLanguage =
            items.isEmpty || items.last.language.isEmpty
                ? null
                : items.last.language;
        final targetLanguage =
            ux.optimisticLanguage ?? station.desired.targetLanguage;
        final processingErrorKey =
            '${station.lastError ?? ''}|${station.sequence}';
        final showProcessingError =
            !station.retrying &&
            (station.lastError?.isNotEmpty ?? false) &&
            _dismissedProcessingError != processingErrorKey;
        void retryConnection() {
          ref.invalidate(apiHealthProvider);
          ref.invalidate(stationProvider(widget.stationId));
          ref.invalidate(liveResultsProvider(resultsKey));
        }

        final body = SingleChildScrollView(
          key: const PageStorageKey('live-scroll'),
          child: Column(
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
                  error: localizedServiceMessage(context, ux.error!),
                  onDismiss: controller.dismissError,
                  showDismiss: !commandFailed,
                  actionLabel:
                      commandFailed ? AppLocalizations.of(context).retry : null,
                  onAction:
                      commandFailed && online && !controller.state.busy
                          ? () => controller.retry(station)
                          : null,
                  secondaryActionLabel:
                      commandFailed ? AppLocalizations.of(context).stop : null,
                  onSecondaryAction:
                      commandFailed && online && !controller.state.busy
                          ? () => controller.setRunning(station, false)
                          : null,
                ),
              if (showProcessingError)
                _CommandErrorBanner(
                  error: localizedServiceMessage(context, station.lastError!),
                  onDismiss:
                      () => setState(
                        () => _dismissedProcessingError = processingErrorKey,
                      ),
                  actionLabel: AppLocalizations.of(context).retry,
                  onAction:
                      online && !ux.busy && !station.retrying
                          ? () => controller.retry(station)
                          : null,
                ),
              LiveFeedHeader(onHistory: _showHistory),
              _TranslationFeed(value: results, onRetry: retryConnection),
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 16),
                child: TxTalkPad(
                  controller: _txController,
                  onReview: _showTxReview,
                  onConnectionRetry: retryConnection,
                ),
              ),
              TxLiveDock(
                controller: _txController,
                stationState: stationDisplayState,
                stationOnline: online,
                apiOnline: apiOnline,
              ),
            ],
          ),
        );
        return ResponsiveScaffold(
          appBar: LiveHeader(
            embedded: widget.embedded,
            toolbarHeight: MediaQuery.textScalerOf(
              context,
            ).scale(44).clamp(64, 120),
            station: station,
            online: online,
            ux: ux,
            txController: _txController,
            onToggle:
                canToggleLiveStation(
                      online: online,
                      running: station.desired.running,
                      busy: ux.busy,
                      commandPending: station.commandPending,
                      commandFailed: commandFailed,
                    )
                    ? () =>
                        controller.setRunning(station, !station.desired.running)
                    : null,
          ),
          body: body,
        );
      },
    );
  }
}
