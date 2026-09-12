part of '../live_screen.dart';

/// The console's hero row: channel, receive state and the capture switch.
///
/// Still named LiveHeader and still the scaffold's app bar slot, because the
/// start/stop logic here is what live_layout_test pins, and it is the part of
/// this screen that must not change while the look does.
class LiveHeader extends StatelessWidget implements PreferredSizeWidget {
  const LiveHeader({
    super.key,
    required this.station,
    required this.online,
    required this.ux,
    required this.onToggle,
    this.txController,
    this.channel,
    this.embedded = false,
    this.toolbarHeight = 64,
  });

  final StationModel station;
  final bool online;
  final LiveUxState ux;
  final VoidCallback? onToggle;
  final TxController? txController;

  /// Null leaves the channel cell out, for callers that have no source.
  final VhfChannel? channel;
  final bool embedded;
  final double toolbarHeight;

  @override
  Size get preferredSize => Size.fromHeight(toolbarHeight);

  @override
  Widget build(BuildContext context) {
    final palette = ConsolePalette.of(context);
    final stationDisplayState = liveStationDisplayState(
      station: station,
      online: online,
      ux: ux,
    );
    final back =
        !embedded && Navigator.of(context).canPop()
            ? SizedBox(width: 48, child: BackButton(color: palette.ink))
            : null;

    Widget rx() =>
        txController == null
            ? _RxCell(stationState: stationDisplayState, online: online)
            : AnimatedBuilder(
              animation: txController!,
              builder:
                  (context, _) => _RxCell(
                    stationState: stationDisplayState,
                    online: online,
                    txActive:
                        txController!.state.phase == TxPhase.recording ||
                        txController!.state.phase == TxPhase.transmitting,
                  ),
            );

    _CaptureCell capture({required bool stacked}) => _CaptureCell(
      station: station,
      online: online,
      ux: ux,
      onToggle: onToggle,
      stacked: stacked,
    );

    return Container(
      key: const ValueKey('live-header'),
      constraints: BoxConstraints(minHeight: toolbarHeight),
      decoration: BoxDecoration(
        color: palette.panel,
        border: Border(bottom: BorderSide(color: palette.hairline)),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          // One row while the capture cell still fits beside the readouts;
          // under a large text scale it drops to its own full-width row
          // rather than squeezing the labels until they clip.
          final scale = MediaQuery.textScalerOf(context);
          final oneRow =
              constraints.maxWidth >=
              scale.scale(channel == null ? 250 : 320) +
                  (back == null ? 0 : 48);
          final readouts = <Widget>[
            if (back != null) back,
            if (channel != null) ...[
              _ChannelCell(channel: channel!, width: constraints.maxWidth),
              _Rule(palette: palette),
            ],
            Expanded(child: rx()),
          ];
          if (oneRow) {
            return IntrinsicHeight(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  ...readouts,
                  _Rule(palette: palette),
                  capture(stacked: false),
                ],
              ),
            );
          }
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            mainAxisSize: MainAxisSize.min,
            children: [
              IntrinsicHeight(
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: readouts,
                ),
              ),
              Divider(height: 1, thickness: 1, color: palette.hairline),
              capture(stacked: true),
            ],
          );
        },
      ),
    );
  }
}

/// A vertical hairline between cells.
class _Rule extends StatelessWidget {
  const _Rule({required this.palette});
  final ConsolePalette palette;

  @override
  Widget build(BuildContext context) =>
      VerticalDivider(width: 1, thickness: 1, color: palette.hairline);
}

class _ChannelCell extends StatelessWidget {
  const _ChannelCell({required this.channel, required this.width});
  final VhfChannel channel;
  final double width;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = ConsolePalette.of(context);
    return Semantics(
      container: true,
      // The dial is not read off the radio yet. The cell shows the number
      // alone, so the disclosure lives here, where it costs no space.
      label:
          '${l10n.liveChannel} ${channel.number} VHF'
          '${channel.simulated ? ', ${l10n.simulatedShort}' : ''}',
      excludeSemantics: true,
      child: Padding(
        key: const ValueKey('live-channel'),
        padding: const EdgeInsets.fromLTRB(14, 10, 14, 10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.center,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              l10n.liveChannel.toUpperCase(),
              style: consoleCaption(palette),
            ),
            const SizedBox(height: 2),
            Row(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.baseline,
              textBaseline: TextBaseline.alphabetic,
              children: [
                Text(
                  '${channel.number}',
                  style: consoleState(
                    palette,
                    size: consoleSize(width, .075, 24, 32),
                    color: palette.accent,
                    weight: FontWeight.w700,
                  ).copyWith(letterSpacing: -.5, height: 1),
                ),
                const SizedBox(width: 4),
                Text('VHF', style: consoleCaption(palette, size: 10)),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _RxCell extends StatelessWidget {
  const _RxCell({
    required this.stationState,
    required this.online,
    this.txActive = false,
  });
  final String stationState;
  final bool online;
  final bool txActive;

  @override
  Widget build(BuildContext context) {
    final palette = ConsolePalette.of(context);
    // The Station reports VAD speech as "recording"; on a radio console that
    // is the channel carrying a transmission, so it reads RECEIVING.
    final state = stationState == 'RECORDING' ? 'RECEIVING' : stationState;
    final label = txActive ? 'TX' : 'RX $state';
    final live =
        txActive || online && (state == 'LISTENING' || state == 'RECEIVING');
    final color =
        txActive || state == 'ERROR'
            ? palette.transmit
            : live || state == 'STARTING' || state == 'STOPPING'
            ? palette.accent
            : palette.muted;
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 10, 12, 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('LIVE VHF', style: consoleCaption(palette)),
          const SizedBox(height: 6),
          Row(
            children: [
              _StateDot(color: color, blinking: live),
              const SizedBox(width: 8),
              Flexible(
                child: Text(
                  label,
                  key: const ValueKey('live-rx-state'),
                  style: consoleState(palette, size: 13, color: palette.ink),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// A state dot that blinks only while the thing it stands for is happening.
///
/// A dot that blinks at idle says "live" when nothing is, and a looping ticker
/// at rest would also keep pumpAndSettle from ever settling.
class _StateDot extends StatefulWidget {
  const _StateDot({required this.color, required this.blinking});
  final Color color;
  final bool blinking;

  @override
  State<_StateDot> createState() => _StateDotState();
}

class _StateDotState extends State<_StateDot>
    with SingleTickerProviderStateMixin {
  late final AnimationController _blink = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 900),
  );

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _sync();
  }

  @override
  void didUpdateWidget(covariant _StateDot oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.blinking != widget.blinking) _sync();
  }

  void _sync() {
    final still = MediaQuery.maybeOf(context)?.disableAnimations ?? false;
    if (widget.blinking && !still) {
      if (!_blink.isAnimating) _blink.repeat(reverse: true);
    } else {
      _blink.stop();
      _blink.value = 0;
    }
  }

  @override
  void dispose() {
    _blink.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => FadeTransition(
    opacity: Tween<double>(begin: 1, end: .25).animate(_blink),
    child: Container(
      width: 8,
      height: 8,
      decoration: BoxDecoration(
        color: widget.color,
        shape: BoxShape.circle,
        boxShadow:
            widget.blinking
                ? [
                  BoxShadow(
                    color: widget.color.withValues(alpha: .6),
                    blurRadius: 6,
                  ),
                ]
                : null,
      ),
    ),
  );
}

class _CaptureCell extends StatelessWidget {
  const _CaptureCell({
    required this.station,
    required this.online,
    required this.ux,
    required this.onToggle,
    required this.stacked,
  });

  final StationModel station;
  final bool online;
  final LiveUxState ux;
  final VoidCallback? onToggle;

  /// On its own full-width row, where it lies flat instead of standing as a
  /// key, so a large text scale does not make the header twice as tall.
  final bool stacked;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = ConsolePalette.of(context);
    final running = station.desired.running;
    // Only a reachable Station can still be working on the command; otherwise
    // the spinner would run forever. See canToggleLiveStation.
    final waiting = ux.busy || (station.commandPending && online);
    final transitionRunning = ux.pendingRunning ?? station.desired.running;
    final buttonRunning = waiting ? transitionRunning : running;
    final background = buttonRunning ? palette.transmit : palette.accent;
    final foreground = buttonRunning ? palette.onTransmit : palette.onAccent;
    final label =
        waiting
            ? (transitionRunning ? l10n.starting : l10n.stopping)
            : (running ? l10n.liveStopCapture : l10n.liveStartCapture);
    final disabled = !waiting && onToggle == null;
    final labelStyle = consoleState(
      palette,
      size: 11,
      color: foreground,
      weight: FontWeight.w700,
    ).copyWith(height: 1.25);
    final scaler = MediaQuery.textScalerOf(context);
    // Lettered on two lines as a key, but never narrower than its longest
    // word: a fixed width would break CAPTURE, or a longer word in another
    // language, in the middle.
    var longestWord = 0.0;
    for (final word in label.split(RegExp(r'\s+'))) {
      final painter = TextPainter(
        text: TextSpan(text: word, style: labelStyle),
        textDirection: Directionality.of(context),
        textScaler: scaler,
        maxLines: 1,
      )..layout();
      if (painter.width > longestWord) longestWord = painter.width;
      painter.dispose();
    }
    final keyWidth = math.max(scaler.scale(64), longestWord.ceilToDouble() + 1);
    return Semantics(
      liveRegion: waiting,
      button: true,
      enabled: !waiting && onToggle != null,
      label: label,
      excludeSemantics: true,
      child: Opacity(
        opacity: disabled ? .45 : 1,
        child: Material(
          key: const ValueKey('live-toggle-button'),
          color: background,
          child: InkWell(
            onTap: waiting ? null : onToggle,
            child: Container(
              constraints: const BoxConstraints(minHeight: 48, minWidth: 92),
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              child: Flex(
                direction: stacked ? Axis.horizontal : Axis.vertical,
                mainAxisAlignment: MainAxisAlignment.center,
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (waiting)
                    SizedBox(
                      key: const ValueKey('live-toggle-progress'),
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(
                        strokeWidth: 2.6,
                        valueColor: AlwaysStoppedAnimation<Color>(foreground),
                      ),
                    )
                  else
                    Icon(
                      running ? Icons.pause : Icons.play_arrow,
                      size: 20,
                      color: foreground,
                    ),
                  SizedBox(width: stacked ? 8 : 0, height: stacked ? 0 : 5),
                  // As a key the label is lettered on two lines; either way it
                  // wraps under a large text scale instead of clipping.
                  Flexible(
                    child: ConstrainedBox(
                      constraints: BoxConstraints(
                        maxWidth: stacked ? double.infinity : keyWidth,
                      ),
                      child: Text(
                        label,
                        key: const ValueKey('live-toggle-label'),
                        textAlign: TextAlign.center,
                        style: labelStyle,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

String liveStationDisplayState({
  required StationModel station,
  required bool online,
  required LiveUxState ux,
}) {
  if (!online) return 'OFF';
  if (station.commandError != null &&
      station.commandFailedGeneration >= station.desired.generation) {
    return 'ERROR';
  }
  if (ux.busy || station.commandPending) {
    final pendingRunning = ux.pendingRunning ?? station.desired.running;
    return pendingRunning ? 'STARTING' : 'STOPPING';
  }
  return station.captureState.toUpperCase();
}
