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
    required this.onReview,
  });

  final TxController controller;
  final String stationState;
  final bool stationOnline;
  final bool apiOnline;
  final VoidCallback onReview;

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: controller,
    builder: (context, _) {
      final state = controller.state;
      final recording = state.phase == TxPhase.recording;
      return Container(
        key: const ValueKey('tx-live-dock'),
        constraints: const BoxConstraints(minHeight: 88),
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
        padding: EdgeInsets.fromLTRB(12, recording ? 6 : 8, 12, 10),
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
            if (state.failure == TxFailure.stationOfflineDuringTx) ...[
              _OfflineTxNotice(settled: state.draft?.status == 'failed'),
              const SizedBox(height: 4),
            ],
            Stack(
              alignment: Alignment.center,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: _RadioStatus(
                        stationState: recording ? 'TX' : stationState,
                        stationOnline: stationOnline,
                        apiOnline: apiOnline,
                      ),
                    ),
                    const SizedBox(width: 128),
                    Expanded(
                      child: _DockLanguage(
                        controller: controller,
                        enabled: state.canChangeLanguage && stationOnline,
                      ),
                    ),
                  ],
                ),
                SizedBox(
                  key: const ValueKey('tx-center-control'),
                  width: 112,
                  child: _CenterControl(
                    controller: controller,
                    onReview: onReview,
                  ),
                ),
              ],
            ),
          ],
        ),
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
  Widget build(BuildContext context) => Column(
    mainAxisSize: MainAxisSize.min,
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      _StatusLine(
        label: stationOnline ? stationState : 'OFFLINE',
        ok: stationOnline,
        tx: stationState == 'TX',
      ),
      const SizedBox(height: 8),
      _StatusLine(
        label: apiOnline ? AppText.of(context, 'api_ready') : 'API OFFLINE',
        ok: apiOnline,
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
  const _CenterControl({required this.controller, required this.onReview});

  final TxController controller;
  final VoidCallback onReview;

  @override
  Widget build(BuildContext context) {
    final state = controller.state;
    if (state.phase == TxPhase.idle || state.phase == TxPhase.recording) {
      return TxPttButton(
        compact: true,
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
      return _DockAction(
        key: const ValueKey('tx-open-review'),
        icon: Icons.rate_review_outlined,
        label: AppText.of(context, 'tx_review_short'),
        onPressed: onReview,
      );
    }
    if (state.phase == TxPhase.completed) {
      return _DockAction(
        icon: Icons.check_circle_outline,
        label: AppText.of(context, 'tx_done_short'),
        onPressed: controller.reset,
      );
    }
    if (state.phase == TxPhase.failed ||
        state.phase == TxPhase.channelBusy ||
        state.phase == TxPhase.expired ||
        state.phase == TxPhase.busy ||
        state.phase == TxPhase.stationOffline) {
      return _DockAction(
        icon:
            state.failure == TxFailure.stationOfflineDuringTx
                ? Icons.cloud_off_outlined
                : Icons.refresh,
        label: AppText.of(
          context,
          state.failure == TxFailure.stationOfflineDuringTx &&
                  !controller.canRetryTransmission
              ? 'waiting'
              : 'retry',
        ),
        onPressed:
            state.draft == null || controller.canRetryTransmission
                ? controller.retry
                : null,
        error: true,
      );
    }
    return _DockProgress(
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

class _DockAction extends StatelessWidget {
  const _DockAction({
    super.key,
    required this.icon,
    required this.label,
    required this.onPressed,
    this.error = false,
  });

  final IconData icon;
  final String label;
  final VoidCallback? onPressed;
  final bool error;

  @override
  Widget build(BuildContext context) => SizedBox(
    height: 58,
    child: FilledButton(
      style: FilledButton.styleFrom(
        padding: const EdgeInsets.symmetric(horizontal: 8),
        backgroundColor:
            error ? Theme.of(context).colorScheme.error : PranaTheme.brandBlue,
      ),
      onPressed: onPressed,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, size: 20),
          const SizedBox(height: 3),
          Text(
            label,
            maxLines: 1,
            style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w900),
          ),
        ],
      ),
    ),
  );
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

class _DockProgress extends StatelessWidget {
  const _DockProgress({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) => Container(
    height: 58,
    padding: const EdgeInsets.symmetric(horizontal: 8),
    decoration: BoxDecoration(
      color: PranaTheme.brandBlueSoft,
      borderRadius: BorderRadius.circular(10),
      border: Border.all(color: const Color(0xFF9EBCC2)),
    ),
    child: Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const SizedBox(
          width: 18,
          height: 18,
          child: CircularProgressIndicator(strokeWidth: 2),
        ),
        const SizedBox(height: 5),
        Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w900),
        ),
      ],
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
    crossAxisAlignment: CrossAxisAlignment.center,
    children: [
      Text(
        AppText.of(context, 'tx_language_short'),
        maxLines: 1,
        textAlign: TextAlign.center,
        style: const TextStyle(
          fontSize: 9,
          fontWeight: FontWeight.w900,
          color: PranaTheme.muted,
          letterSpacing: .5,
        ),
      ),
      const SizedBox(height: 4),
      LayoutBuilder(
        builder: (context, constraints) {
          final width = constraints.maxWidth < 96 ? constraints.maxWidth : 96.0;
          return Align(
            alignment: Alignment.center,
            child: SizedBox(
              width: width,
              child: PopupMenuButton<String>(
                key: const ValueKey('tx-dock-language'),
                enabled: enabled,
                padding: EdgeInsets.zero,
                position: PopupMenuPosition.over,
                tooltip: AppText.of(context, 'tx_language_short'),
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
                                    if (entry.key ==
                                        controller.state.targetLanguage)
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
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Flexible(
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
                          fontSize: 12,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Icon(
                      Icons.keyboard_arrow_down,
                      key: const ValueKey('tx-language-chevron'),
                      size: 16,
                      color:
                          enabled
                              ? PranaTheme.muted
                              : Theme.of(context).disabledColor,
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    ],
  );
}
