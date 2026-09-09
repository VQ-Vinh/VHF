part of '../live_screen.dart';

class LiveHeader extends StatelessWidget implements PreferredSizeWidget {
  const LiveHeader({
    super.key,
    required this.station,
    required this.online,
    required this.ux,
    required this.onToggle,
    this.txController,
    this.embedded = false,
    this.toolbarHeight = 64,
  });

  final StationModel station;
  final bool online;
  final LiveUxState ux;
  final VoidCallback? onToggle;
  final TxController? txController;
  final bool embedded;
  final double toolbarHeight;

  @override
  Size get preferredSize => Size.fromHeight(toolbarHeight);

  @override
  Widget build(BuildContext context) {
    final running = station.desired.running;
    // Only a reachable Station can still be working on the command; otherwise
    // the spinner would run forever. See canToggleLiveStation.
    final waiting = ux.busy || (station.commandPending && online);
    final transitionRunning = ux.pendingRunning ?? station.desired.running;
    final buttonRunning = waiting ? transitionRunning : running;
    final stationDisplayState = liveStationDisplayState(
      station: station,
      online: online,
      ux: ux,
    );
    return ResponsiveHeader(
      key: const ValueKey('live-header'),
      stackActions:
          MediaQuery.textScalerOf(context).scale(320) >
          MediaQuery.sizeOf(context).width,
      automaticallyImplyLeading: !embedded,
      toolbarHeight: toolbarHeight,
      leadingWidth: 44,
      titleSpacing: 0,
      title: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            embedded ? 'Live VHF' : station.name,
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
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 10),
          child: Semantics(
            liveRegion: waiting,
            button: true,
            enabled: !waiting && onToggle != null,
            label:
                waiting
                    ? (transitionRunning
                        ? AppLocalizations.of(context).starting
                        : AppLocalizations.of(context).stopping)
                    : (running
                        ? AppLocalizations.of(context).stop
                        : AppLocalizations.of(context).start),
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
                child: Container(
                  constraints: const BoxConstraints(minHeight: 48),
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 12,
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
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
                              ? (transitionRunning
                                  ? AppLocalizations.of(context).starting
                                  : AppLocalizations.of(context).stopping)
                              : (running
                                  ? AppLocalizations.of(context).stop
                                  : AppLocalizations.of(context).start),
                          key: const ValueKey('live-toggle-label'),
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
