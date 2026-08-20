import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../../../core/localization.dart';
import '../../../../core/languages.dart';
import '../../../../core/theme.dart';
import '../../application/tx_controller.dart';
import '../../domain/tx_failure.dart';
import '../../domain/tx_phase.dart';
import 'tx_ptt_button.dart';

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
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Expanded(
              flex: 3,
              child: SizedBox(
                height: 40,
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
            const SizedBox(width: 10),
            Expanded(
              flex: 2,
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
          // Whatever the status lines above the circle need, plus room for the
          // 1.08 recording pulse, so the circle can never overflow the pad.
          final reserved = (recording ? 28.0 : 0) + (notice ? 26.0 : 0) + 16;
          final available = math.max(constraints.maxHeight - reserved, 0.0);
          final diameter = math
              .min(available / 1.08, constraints.maxWidth * .58)
              .clamp(112.0, 200.0);
          // Landscape leaves the pad shorter than the smallest circle plus the
          // fixed-height phase controls, so scale the block down rather than
          // let it overflow.
          return Center(
            child: FittedBox(
              fit: BoxFit.scaleDown,
              // FittedBox hands its child unbounded width, which breaks the
              // Flexible status rows; pin it back to the pad's width.
              child: SizedBox(
                width: constraints.maxWidth,
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
                      _OfflineTxNotice(
                        settled: state.draft?.status == 'failed',
                      ),
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
          label: apiOnline ? AppText.of(context, 'api_ready') : 'API OFFLINE',
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
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
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
        disabledTextKey:
            controller.startRequired ? 'tx_start_required_short' : null,
        maximumSeconds: controller.recordingMaximumDuration.inSeconds,
      );
    }
    if (state.phase == TxPhase.reviewReady) {
      return _PhaseCircle(
        key: const ValueKey('tx-open-review'),
        diameter: diameter,
        icon: Icons.rate_review_outlined,
        label: AppText.of(context, 'tx_review_short'),
        onPressed: onReview,
      );
    }
    if (state.phase == TxPhase.completed) {
      // Not a button: the controller clears this on its own after a moment.
      return _PhaseCircle(
        key: const ValueKey('tx-done-indicator'),
        diameter: diameter,
        icon: Icons.check_circle_outline,
        label: AppText.of(context, 'tx_done_short'),
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
        label: AppText.of(
          context,
          state.failure == TxFailure.stationOfflineDuringTx &&
                      !controller.canRetryTransmission ||
                  state.failure == TxFailure.pttUnavailable
              ? 'waiting'
              : 'retry',
        ),
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
      label: AppText.of(
        context,
        state.phase == TxPhase.processing
            ? 'tx_processing_short'
            : state.phase == TxPhase.queued
            ? 'tx_queued_short'
            : 'tx_transmitting_short',
      ),
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
            ? PranaTheme.brandBlueSoft
            : disabled
            ? const Color(0xFFB8C7CB)
            : error
            ? Theme.of(context).colorScheme.error
            : PranaTheme.brandBlue;
    final foreground = muted ? PranaTheme.brandBlue : Colors.white;
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
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
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
        '${AppText.of(context, 'tx_recording_short')} ${_clock(duration)} / ${_clock(maximumDuration)}',
    child: Container(
      key: const ValueKey('tx-recording-status'),
      height: 24,
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
              '${AppText.of(context, 'tx_recording_short')} • ${_clock(duration)} / ${_clock(maximumDuration)} · ${AppText.of(context, 'tx_release_hint')}',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
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
    AppText.of(
      context,
      settled ? 'tx_station_offline_during_tx' : 'tx_retry_waiting_station',
    ),
    key: const ValueKey('tx-offline-notice'),
    maxLines: 2,
    textAlign: TextAlign.center,
    overflow: TextOverflow.ellipsis,
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
        AppText.of(context, 'tx_transmit_in').toUpperCase(),
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: const TextStyle(
          fontSize: 10,
          fontWeight: FontWeight.w800,
          color: PranaTheme.muted,
          letterSpacing: .7,
        ),
      ),
      const SizedBox(height: 1),
      PopupMenuButton<String>(
        key: const ValueKey('tx-dock-language'),
        enabled: enabled,
        padding: EdgeInsets.zero,
        position: PopupMenuPosition.over,
        tooltip: AppText.of(context, 'tx_transmit_in'),
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
          height: 40,
          width: double.infinity,
          alignment: Alignment.centerLeft,
          padding: const EdgeInsets.symmetric(horizontal: 11),
          decoration: BoxDecoration(
            color: PranaTheme.surface,
            border: Border.all(color: const Color(0xFFB9CDD2)),
            borderRadius: BorderRadius.circular(11),
          ),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  supportedLanguages[controller.state.targetLanguage] ??
                      controller.state.targetLanguage.toUpperCase(),
                  key: const ValueKey('tx-language-value'),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color:
                        enabled
                            ? PranaTheme.navy
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
                        ? PranaTheme.muted
                        : Theme.of(context).disabledColor,
              ),
            ],
          ),
        ),
      ),
    ],
  );
}
