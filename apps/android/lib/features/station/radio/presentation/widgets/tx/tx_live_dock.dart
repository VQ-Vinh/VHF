import 'package:prana_mobile/l10n/app_localizations.dart';
import 'dart:math' as math;

import 'package:flutter/material.dart';

import 'package:prana_mobile/runtime/vhf/tx_controller.dart';
import 'package:prana_mobile/domain/radio/tx/tx_failure.dart';
import 'package:prana_mobile/domain/radio/tx/tx_phase.dart';
import 'package:prana_mobile/features/station/radio/presentation/widgets/console_language_menu.dart';
import 'package:prana_mobile/features/station/radio/presentation/widgets/console_palette.dart';
import 'package:prana_mobile/features/station/radio/presentation/widgets/tx/ptt_instrument.dart';
import 'package:prana_mobile/features/station/radio/presentation/widgets/tx/tx_ptt_button.dart';

/// The bottom of the console: the transmit language with its TX key, and the
/// status strip under it.
class TxLiveDock extends StatelessWidget {
  const TxLiveDock({
    super.key,
    required this.controller,
    required this.stationOnline,
    required this.apiOnline,
    this.now,
    this.onReview,
  });

  final TxController controller;
  final bool stationOnline;
  final bool apiOnline;

  /// Station clock, shown in UTC. Null hides the clock.
  final DateTime? now;

  /// Opens the review sheet, which is where a draft is actually sent.
  final VoidCallback? onReview;

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: controller,
    builder: (context, _) {
      final l10n = AppLocalizations.of(context);
      final palette = ConsolePalette.of(context);
      final state = controller.state;
      final recording = state.phase == TxPhase.recording;
      final enabled = state.canChangeLanguage && stationOnline;
      return Container(
        key: const ValueKey('tx-live-dock'),
        decoration: BoxDecoration(
          color: palette.panel,
          border: Border(
            top: BorderSide(
              color: recording ? palette.transmit : palette.hairline,
              width: recording ? 2 : 1,
            ),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            IntrinsicHeight(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(14, 10, 12, 4),
                      child: ConsoleField(
                        key: const ValueKey('tx-language-region'),
                        caption: l10n.txTransmitIn,
                        child: ConsoleLanguageMenu(
                          key: const ValueKey('tx-dock-language'),
                          value: state.targetLanguage,
                          enabled: enabled,
                          onSelected: controller.setTargetLanguage,
                          tooltip: l10n.txTransmitIn,
                          valueKey: const ValueKey('tx-language-value'),
                          chevronKey: const ValueKey('tx-language-chevron'),
                        ),
                      ),
                    ),
                  ),
                  VerticalDivider(
                    width: 1,
                    thickness: 1,
                    color: palette.hairline,
                  ),
                  _TxCell(phase: state.phase, onReview: onReview),
                ],
              ),
            ),
            Divider(height: 1, thickness: 1, color: palette.hairline),
            _StatusStrip(
              phase: state.phase,
              stationOnline: stationOnline,
              apiOnline: apiOnline,
              now: now,
            ),
          ],
        ),
      );
    },
  );
}

/// The step that sends. It lights once a draft is ready for review, because
/// review is where a transmission is confirmed; before that there is nothing
/// to send, and while one is queued or on air it shows that instead.
class _TxCell extends StatelessWidget {
  const _TxCell({required this.phase, required this.onReview});
  final TxPhase phase;
  final VoidCallback? onReview;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = ConsolePalette.of(context);
    final ready = phase == TxPhase.reviewReady && onReview != null;
    final onAir = phase == TxPhase.transmitting;
    final queued = phase == TxPhase.queued;
    final color =
        onAir
            ? palette.transmit
            : ready || queued
            ? palette.accent
            : palette.muted;
    return Semantics(
      button: true,
      enabled: ready,
      label: ready ? '${l10n.txReviewShort} TX' : 'TX',
      excludeSemantics: true,
      child: Material(
        type: MaterialType.transparency,
        child: InkWell(
          key: const ValueKey('tx-send-cell'),
          onTap: ready ? onReview : null,
          child: Container(
            constraints: const BoxConstraints(minWidth: 76, minHeight: 48),
            color: ready ? palette.accent.withValues(alpha: .10) : null,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            alignment: Alignment.center,
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.wifi_tethering, size: 18, color: color),
                const SizedBox(width: 6),
                Text(
                  'TX',
                  key: const ValueKey('tx-send-label'),
                  style: consoleState(palette, size: 13, color: color),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// TX state, the API link and the time, on one strip that wraps rather than
/// clips when the text is large.
class _StatusStrip extends StatelessWidget {
  const _StatusStrip({
    required this.phase,
    required this.stationOnline,
    required this.apiOnline,
    required this.now,
  });
  final TxPhase phase;
  final bool stationOnline;
  final bool apiOnline;
  final DateTime? now;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = ConsolePalette.of(context);
    // Recording is not transmitting: the voice is captured for translation
    // and nothing is on air until the draft has been confirmed.
    final (label, tone) = switch (phase) {
      TxPhase.idle =>
        stationOnline ? ('IDLE', palette.muted) : ('OFFLINE', palette.transmit),
      TxPhase.recording => (l10n.txRecordingShort, palette.transmit),
      TxPhase.processing => (l10n.txProcessingShort, palette.accent),
      TxPhase.reviewReady => (l10n.txReviewShort, palette.accent),
      TxPhase.queued => (l10n.txQueuedShort, palette.accent),
      TxPhase.transmitting => (l10n.txTransmittingShort, palette.transmit),
      TxPhase.completed => (l10n.txDoneShort, palette.ok),
      TxPhase.channelBusy => ('CHANNEL BUSY', palette.transmit),
      TxPhase.stationOffline => ('OFFLINE', palette.transmit),
      TxPhase.busy ||
      TxPhase.expired ||
      TxPhase.failed => ('FAILED', palette.transmit),
    };
    final utc = now?.toUtc();
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 8, 14, 8),
      child: Wrap(
        alignment: WrapAlignment.spaceBetween,
        crossAxisAlignment: WrapCrossAlignment.center,
        spacing: 12,
        runSpacing: 4,
        children: [
          Wrap(
            crossAxisAlignment: WrapCrossAlignment.center,
            spacing: 14,
            runSpacing: 4,
            children: [
              _StatusItem(
                key: const ValueKey('tx-status-state'),
                label: label,
                color: tone,
              ),
              _StatusItem(
                label: apiOnline ? l10n.apiReady : 'API OFFLINE',
                color: apiOnline ? palette.ok : palette.transmit,
              ),
            ],
          ),
          if (utc != null)
            Text(
              '${utc.hour.toString().padLeft(2, '0')}:'
              '${utc.minute.toString().padLeft(2, '0')} UTC',
              key: const ValueKey('tx-status-clock'),
              style: consoleState(palette, size: 11, color: palette.muted),
            ),
        ],
      ),
    );
  }
}

class _StatusItem extends StatelessWidget {
  const _StatusItem({super.key, required this.label, required this.color});
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final palette = ConsolePalette.of(context);
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 7,
          height: 7,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 6),
        Flexible(
          child: Text(
            label,
            style: consoleState(palette, size: 11, color: palette.ink),
          ),
        ),
      ],
    );
  }
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
    this.channelState = PttChannelState.idle,
  });

  final TxController controller;
  final VoidCallback onReview;
  final VoidCallback onConnectionRetry;

  /// What the receive side is doing, for the instrument around the key.
  /// Holding the key or transmitting overrides it.
  final PttChannelState channelState;

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: controller,
    builder: (context, _) {
      final state = controller.state;
      final recording = state.phase == TxPhase.recording;
      final notice = state.failure == TxFailure.stationOfflineDuringTx;
      final transmit = recording || state.phase == TxPhase.transmitting;
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
          // The rings take what is left around the key and give way first,
          // in both directions: under a large text scale, or in a pad the
          // dock has left short, the key keeps its size and the instrument
          // thins down to it. Rings that pushed the key out of a short pad
          // would put the one control that matters below the fold.
          final room =
              constraints.hasBoundedHeight
                  ? constraints.maxHeight -
                      24 -
                      (recording ? 28 : 0) -
                      (notice ? 24 : 0)
                  : double.infinity;
          final outer = math.max(
            diameter,
            math.min(math.min(diameter * 1.45, constraints.maxWidth - 8), room),
          );
          return SingleChildScrollView(
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 12),
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
                  PttInstrument(
                    state: transmit ? PttChannelState.transmit : channelState,
                    buttonDiameter: diameter,
                    outerDiameter: outer,
                    child: _CenterControl(
                      key: const ValueKey('tx-center-control'),
                      controller: controller,
                      diameter: diameter,
                      onReview: onReview,
                      onConnectionRetry: onConnectionRetry,
                    ),
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
    final palette = ConsolePalette.of(context);
    final disabled = onPressed == null && !muted;
    // Same key shape and ink as the PTT: panel fill ringed in the state's
    // colour, so the control reads as one instrument through every phase.
    final tone =
        disabled
            ? palette.muted
            : error
            ? palette.transmit
            : palette.accent;
    final background = palette.panel;
    final foreground = disabled ? palette.muted : palette.ink;
    final circle = Container(
      width: diameter,
      height: diameter,
      padding: EdgeInsets.symmetric(horizontal: diameter * .12),
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: background,
        border: Border.all(
          color: muted ? palette.hairline : tone,
          width: muted ? 1 : 2,
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
                valueColor: AlwaysStoppedAnimation<Color>(tone),
              ),
            )
          else
            Icon(icon, size: diameter * .24, color: tone),
          SizedBox(height: diameter * .05),
          Text(
            label,
            textAlign: TextAlign.center,

            style: consoleState(
              palette,
              size: (diameter * .075).clamp(10.0, 14.0),
              color: foreground,
            ).copyWith(letterSpacing: 1),
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
        color: ConsolePalette.of(context).transmit.withValues(alpha: .12),
        border: Border(
          left: BorderSide(
            color: ConsolePalette.of(context).transmit,
            width: 2,
          ),
        ),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.fiber_manual_record,
            size: 11,
            color: ConsolePalette.of(context).transmit,
          ),
          const SizedBox(width: 5),
          Flexible(
            child: Text(
              '${AppLocalizations.of(context).txRecordingShort} • ${_clock(duration)} / ${_clock(maximumDuration)} · ${AppLocalizations.of(context).txReleaseHint}',

              style: consoleState(
                ConsolePalette.of(context),
                size: 10,
                color: ConsolePalette.of(context).transmit,
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

    style: consoleState(
      ConsolePalette.of(context),
      size: 10,
      color: ConsolePalette.of(context).transmit,
      weight: FontWeight.w600,
    ),
  );
}
