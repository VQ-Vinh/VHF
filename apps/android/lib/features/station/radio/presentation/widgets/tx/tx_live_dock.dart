import 'package:prana_mobile/l10n/app_localizations.dart';
import 'package:prana_mobile/core/responsive.dart';
import 'dart:math' as math;

import 'package:flutter/material.dart';

import 'package:prana_mobile/core/languages.dart';
import 'package:prana_mobile/core/theme.dart';
import 'package:prana_mobile/runtime/vhf/tx_controller.dart';
import 'package:prana_mobile/domain/radio/tx/tx_failure.dart';
import 'package:prana_mobile/domain/radio/tx/tx_phase.dart';
import 'package:prana_mobile/features/station/radio/presentation/widgets/tx/tx_ptt_button.dart';

class TxLiveDock extends StatelessWidget {
  const TxLiveDock({
    super.key,
    required this.controller,
    required this.stationState,
    required this.stationOnline,
    required this.apiOnline,
  });

  final TxController controller;
  final String stationState;
  final bool stationOnline;
  final bool apiOnline;

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: controller,
    builder: (context, _) {
      final state = controller.state;
      final recording = state.phase == TxPhase.recording;
      return Container(
        key: const ValueKey('tx-live-dock'),
        decoration: BoxDecoration(
          color: recording ? const Color(0xFFFFF3F4) : const Color(0xFFDCE9ED),
        ),
        foregroundDecoration: BoxDecoration(
          border: Border(
            top: BorderSide(
              color:
                  recording ? const Color(0xFFC33F4F) : const Color(0xFFC5DADF),
              width: recording ? 2 : 1,
            ),
          ),
        ),
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 10),
        child: AdaptiveFields(
          minimumWidth: 150,
          children: [
            SizedBox(
              child: ConstrainedBox(
                constraints: const BoxConstraints(minHeight: 48),
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: _RadioStatus(
                    stationState: recording ? 'TX' : stationState,
                    stationOnline: stationOnline,
                    apiOnline: apiOnline,
                  ),
                ),
              ),
            ),
            SizedBox(
              child: _DockLanguage(
                controller: controller,
                enabled: state.canChangeLanguage && stationOnline,
              ),
            ),
          ],
        ),
      );
    },
  );
}

/// The talk control lifted out of the dock so the circle can float in the free
/// space above it. Every [TxPhase] renders here, so the control never jumps
/// between two regions of the screen as the transmission progresses.
class TxTalkPad extends StatelessWidget {
  const TxTalkPad({
    super.key,
    required this.controller,
    required this.onReview,
    required this.onConnectionRetry,
  });

  final TxController controller;
  final VoidCallback onReview;
  final VoidCallback onConnectionRetry;

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: controller,
    builder: (context, _) {
      final state = controller.state;
      final recording = state.phase == TxPhase.recording;
      final notice = state.failure == TxFailure.stationOfflineDuringTx;
      return LayoutBuilder(
        key: const ValueKey('tx-talk-pad'),
        builder: (context, constraints) {
          final diameter =
              math
                  .min(
                    math.max(48, constraints.maxWidth - 32),
                    MediaQuery.textScalerOf(context).scale(200),
                  )
                  .toDouble();
          return SingleChildScrollView(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (recording) ...[
                    _RecordingStatus(
                      duration: state.duration,
                      maximumDuration: controller.recordingMaximumDuration,
                    ),
                    const SizedBox(height: 4),
                  ],
                  if (notice) ...[
                    _OfflineTxNotice(settled: state.draft?.status == 'failed'),
                    const SizedBox(height: 4),
                  ],
                  _CenterControl(
                    key: const ValueKey('tx-center-control'),
                    controller: controller,
                    diameter: diameter,
                    onReview: onReview,
                    onConnectionRetry: onConnectionRetry,
                  ),
                ],
              ),
            ),
          );
        },
      );
    },
  );
}

class _RadioStatus extends StatelessWidget {
  const _RadioStatus({
    required this.stationState,
    required this.stationOnline,
    required this.apiOnline,
  });

  final String stationState;
  final bool stationOnline;
  final bool apiOnline;

  @override
  // Height matches the language field beside it so the two read as one band.
  Widget build(BuildContext context) => Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      Flexible(
        child: _StatusLine(
          label: stationOnline ? stationState : 'OFFLINE',
          ok: stationOnline,
          tx: stationState == 'TX',
        ),
      ),
      const SizedBox(width: 12),
      Flexible(
        child: _StatusLine(
          label:
              apiOnline ? AppLocalizations.of(context).apiReady : 'API OFFLINE',
          ok: apiOnline,
        ),
      ),
    ],
  );
}

class _StatusLine extends StatelessWidget {
  const _StatusLine({required this.label, required this.ok, this.tx = false});

  final String label;
  final bool ok;
  final bool tx;

  @override
  Widget build(BuildContext context) => Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      Icon(
        Icons.circle,
        size: 7,
        color:
            tx
                ? const Color(0xFFC33F4F)
                : ok
                ? const Color(0xFF21835A)
                : const Color(0xFFC34655),
      ),
      const SizedBox(width: 6),
      Flexible(
        child: Text(
          label,

          style: TextStyle(
            fontSize: 10,
            fontWeight: FontWeight.w900,
            color: tx ? const Color(0xFF9E2637) : const Color(0xFF355762),
          ),
        ),
      ),
    ],
  );
}

class _CenterControl extends StatelessWidget {
  const _CenterControl({
    super.key,
    required this.controller,
    required this.diameter,
    required this.onReview,
    required this.onConnectionRetry,
  });

  final TxController controller;
  final double diameter;
  final VoidCallback onReview;
  final VoidCallback onConnectionRetry;

  @override
  Widget build(BuildContext context) {
    final state = controller.state;
    if (state.phase == TxPhase.idle || state.phase == TxPhase.recording) {
      return TxPttButton(
        diameter: diameter,
        enabled: controller.canStartRecording,
        recording: state.phase == TxPhase.recording,
        onHoldStart: controller.startRecording,
        onHoldEnd: controller.stopRecording,
        disabledText:
            controller.startRequired
                ? AppLocalizations.of(context).txStartRequiredShort
                : null,
        maximumSeconds: controller.recordingMaximumDuration.inSeconds,
      );
    }
    if (state.phase == TxPhase.reviewReady) {
      return _PhaseCircle(
        key: const ValueKey('tx-open-review'),
        diameter: diameter,
        icon: Icons.rate_review_outlined,
        label: AppLocalizations.of(context).txReviewShort,
        onPressed: onReview,
      );
    }
    if (state.phase == TxPhase.completed) {
      // Not a button: the controller clears this on its own after a moment.
      return _PhaseCircle(
        key: const ValueKey('tx-done-indicator'),
        diameter: diameter,
        icon: Icons.check_circle_outline,
        label: AppLocalizations.of(context).txDoneShort,
        muted: true,
      );
    }
    if (state.phase == TxPhase.failed ||
        state.phase == TxPhase.channelBusy ||
        state.phase == TxPhase.expired ||
        state.phase == TxPhase.busy ||
        state.phase == TxPhase.stationOffline) {
      final retryConnection =
          state.draft == null && state.failure == TxFailure.stationOffline;
      return _PhaseCircle(
        diameter: diameter,
        icon:
            state.failure == TxFailure.stationOfflineDuringTx
                ? Icons.cloud_off_outlined
                : Icons.refresh,
        label:
            (state.failure == TxFailure.stationOfflineDuringTx &&
                        !controller.canRetryTransmission ||
                    state.failure == TxFailure.pttUnavailable
                ? AppLocalizations.of(context).waiting
                : AppLocalizations.of(context).retry),
        onPressed:
            retryConnection
                ? onConnectionRetry
                : (state.draft == null &&
                        state.failure != TxFailure.pttUnavailable) ||
                    controller.canRetryTransmission
                ? controller.retry
                : null,
        error: true,
      );
    }
    return _PhaseCircle(
      diameter: diameter,
      muted: true,
      label:
          (state.phase == TxPhase.processing
              ? AppLocalizations.of(context).txProcessingShort
              : state.phase == TxPhase.queued
              ? AppLocalizations.of(context).txQueuedShort
              : AppLocalizations.of(context).txTransmittingShort),
    );
  }
}

/// Every non-recording TX phase renders as the same circle as the PTT button,
/// so the control keeps one shape and one footprint across the whole flow.
class _PhaseCircle extends StatelessWidget {
  const _PhaseCircle({
    super.key,
    required this.diameter,
    required this.label,
    this.icon,
    this.onPressed,
    this.error = false,
    this.muted = false,
  });

  final double diameter;
  final String label;

  /// Null renders a spinner instead: the step is still in flight.
  final IconData? icon;
  final VoidCallback? onPressed;
  final bool error;

  /// Soft fill for steps the user only watches rather than acts on.
  final bool muted;

  @override
  Widget build(BuildContext context) {
    final disabled = onPressed == null && !muted;
    final background =
        muted
            ? Theme.of(context).colorScheme.primaryContainer
            : disabled
            ? const Color(0xFFB8C7CB)
            : error
            ? Theme.of(context).colorScheme.error
            : PranaTheme.brandBlue;
    final foreground =
        muted ? Theme.of(context).colorScheme.onPrimaryContainer : Colors.white;
    final circle = Container(
      width: diameter,
      height: diameter,
      padding: EdgeInsets.symmetric(horizontal: diameter * .12),
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: background,
        border:
            muted
                ? Border.all(color: const Color(0xFF9EBCC2))
                : Border.all(
                  color: background.withValues(alpha: .22),
                  width: 10,
                ),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          if (icon == null)
            SizedBox(
              width: diameter * .22,
              height: diameter * .22,
              child: CircularProgressIndicator(
                strokeWidth: 3,
                valueColor: AlwaysStoppedAnimation<Color>(foreground),
              ),
            )
          else
            Icon(icon, size: diameter * .26, color: foreground),
          SizedBox(height: diameter * .05),
          Text(
            label,
            textAlign: TextAlign.center,

            style: TextStyle(
              color: foreground,
              fontSize: (diameter * .085).clamp(11, 15),
              fontWeight: FontWeight.w900,
              letterSpacing: .4,
            ),
          ),
        ],
      ),
    );
    if (onPressed == null) return circle;
    return Material(
      type: MaterialType.transparency,
      child: InkWell(
        customBorder: const CircleBorder(),
        onTap: onPressed,
        child: circle,
      ),
    );
  }
}

class _RecordingStatus extends StatelessWidget {
  const _RecordingStatus({
    required this.duration,
    required this.maximumDuration,
  });

  final Duration duration;
  final Duration maximumDuration;

  String _clock(Duration value) {
    final seconds = value.inSeconds.clamp(0, 120);
    final minutes = seconds ~/ 60;
    final remainder = seconds % 60;
    return '${minutes.toString().padLeft(2, '0')}:${remainder.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) => Semantics(
    liveRegion: true,
    label:
        '${AppLocalizations.of(context).txRecordingShort} ${_clock(duration)} / ${_clock(maximumDuration)}',
    child: Container(
      key: const ValueKey('tx-recording-status'),
      constraints: const BoxConstraints(minHeight: 24),
      padding: const EdgeInsets.symmetric(horizontal: 10),
      decoration: BoxDecoration(
        color: const Color(0xFFFFE7EA),
        borderRadius: BorderRadius.circular(7),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(
            Icons.fiber_manual_record,
            size: 11,
            color: Color(0xFFC33F4F),
          ),
          const SizedBox(width: 5),
          Flexible(
            child: Text(
              '${AppLocalizations.of(context).txRecordingShort} • ${_clock(duration)} / ${_clock(maximumDuration)} · ${AppLocalizations.of(context).txReleaseHint}',

              style: const TextStyle(
                color: Color(0xFF9E2637),
                fontSize: 10,
                fontWeight: FontWeight.w900,
              ),
            ),
          ),
        ],
      ),
    ),
  );
}

class _OfflineTxNotice extends StatelessWidget {
  const _OfflineTxNotice({required this.settled});

  final bool settled;

  @override
  Widget build(BuildContext context) => Text(
    (settled
        ? AppLocalizations.of(context).txStationOfflineDuringTx
        : AppLocalizations.of(context).txRetryWaitingStation),
    key: const ValueKey('tx-offline-notice'),
    textAlign: TextAlign.center,

    style: const TextStyle(
      color: Color(0xFF9E2637),
      fontSize: 9,
      fontWeight: FontWeight.w800,
    ),
  );
}

class _DockLanguage extends StatelessWidget {
  const _DockLanguage({required this.controller, required this.enabled});

  final TxController controller;
  final bool enabled;

  @override
  Widget build(BuildContext context) => Column(
    key: const ValueKey('tx-language-region'),
    mainAxisSize: MainAxisSize.min,
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      // Mirrors _LanguageLabel of the RX strip, which uppercases the same
      // Title Case entry the tooltip below shows as written.
      Text(
        AppLocalizations.of(context).txTransmitIn.toUpperCase(),

        style: TextStyle(
          fontSize: 10,
          fontWeight: FontWeight.w800,
          color: Theme.of(context).colorScheme.onSurfaceVariant,
          letterSpacing: .7,
        ),
      ),
      const SizedBox(height: 1),
      PopupMenuButton<String>(
        key: const ValueKey('tx-dock-language'),
        enabled: enabled,
        padding: EdgeInsets.zero,
        position: PopupMenuPosition.over,
        tooltip: AppLocalizations.of(context).txTransmitIn,
        onSelected: controller.setTargetLanguage,
        itemBuilder:
            (context) =>
                supportedLanguages.entries
                    .map(
                      (entry) => PopupMenuItem<String>(
                        value: entry.key,
                        child: Row(
                          children: [
                            Expanded(child: Text(entry.value)),
                            if (entry.key == controller.state.targetLanguage)
                              const Icon(
                                Icons.check,
                                size: 18,
                                color: PranaTheme.brandBlue,
                              ),
                          ],
                        ),
                      ),
                    )
                    .toList(),
        // Same frame as _LanguageValue on the INPUT/OUTPUT strip, whose border
        // and radius come from theme.dart's inputDecorationTheme.
        child: Container(
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
          child: Row(
            children: [
              Expanded(
                child: Text(
                  supportedLanguages[controller.state.targetLanguage] ??
                      controller.state.targetLanguage.toUpperCase(),
                  key: const ValueKey('tx-language-value'),

                  style: TextStyle(
                    color:
                        enabled
                            ? Theme.of(context).colorScheme.onSurface
                            : Theme.of(context).disabledColor,
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              Icon(
                Icons.arrow_drop_down,
                key: const ValueKey('tx-language-chevron'),
                color:
                    enabled
                        ? Theme.of(context).colorScheme.onSurfaceVariant
                        : Theme.of(context).disabledColor,
              ),
            ],
          ),
        ),
      ),
    ],
  );
}
