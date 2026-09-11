import 'package:prana_mobile/l10n/app_localizations.dart';
import 'package:flutter/material.dart';

import 'package:prana_mobile/features/station/radio/presentation/widgets/console_palette.dart';

/// The hold-to-talk key at the centre of the PTT instrument.
///
/// Holding records the voice to be translated; nothing goes on air until the
/// draft has been reviewed and confirmed. So the held label says to release,
/// not that the operator is on air, which on a radio would be a false claim.
class TxPttButton extends StatefulWidget {
  const TxPttButton({
    super.key,
    required this.enabled,
    required this.recording,
    required this.onHoldStart,
    required this.onHoldEnd,
    this.diameter = 168,
    this.disabledText,
    this.maximumSeconds = 60,
  });

  final bool enabled;
  final bool recording;
  final VoidCallback onHoldStart;
  final VoidCallback onHoldEnd;
  final double diameter;
  final String? disabledText;
  final int maximumSeconds;

  @override
  State<TxPttButton> createState() => _TxPttButtonState();
}

class _TxPttButtonState extends State<TxPttButton>
    with SingleTickerProviderStateMixin {
  late final AnimationController _glow = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 850),
  );

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _syncGlow();
  }

  @override
  void didUpdateWidget(covariant TxPttButton oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.recording != widget.recording) _syncGlow();
  }

  void _syncGlow() {
    final reduceMotion =
        MediaQuery.maybeOf(context)?.disableAnimations ?? false;
    if (widget.recording && !reduceMotion) {
      if (!_glow.isAnimating) _glow.repeat(reverse: true);
    } else {
      _glow.stop();
      _glow.value = 0;
    }
  }

  @override
  void dispose() {
    _glow.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = ConsolePalette.of(context);
    final held = widget.recording;
    final enabled = widget.enabled;
    final fill =
        held
            ? palette.transmit
            : enabled
            ? palette.panel
            : palette.hairline;
    final ring =
        held
            ? palette.transmit.withValues(alpha: .35)
            : enabled
            ? palette.accent
            : palette.muted.withValues(alpha: .5);
    final ink =
        held
            ? palette.onTransmit
            : enabled
            ? palette.ink
            : palette.muted;
    final labelSize = (widget.diameter * .075).clamp(10.0, 14.0);
    return Semantics(
      button: true,
      enabled: enabled,
      liveRegion: held,
      label: held ? l10n.txRecording : l10n.txHoldToTalk,
      hint: l10n.txMaxDuration(widget.maximumSeconds.toString()),
      child: Listener(
        key: const ValueKey('tx-ptt-button'),
        onPointerDown: enabled ? (_) => widget.onHoldStart() : null,
        onPointerUp: enabled || held ? (_) => widget.onHoldEnd() : null,
        onPointerCancel: enabled || held ? (_) => widget.onHoldEnd() : null,
        // Pressed in, like a key under a thumb. A transform, so the layout
        // size never changes under a held pointer.
        child: AnimatedScale(
          scale: held ? .96 : 1,
          duration: const Duration(milliseconds: 120),
          child: AnimatedBuilder(
            animation: _glow,
            builder:
                (context, child) => SizedBox(
                  width: widget.diameter,
                  height: widget.diameter,
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 160),
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: fill,
                      border: Border.all(color: ring, width: held ? 8 : 2),
                      boxShadow:
                          held
                              ? [
                                BoxShadow(
                                  color: palette.transmit.withValues(
                                    alpha: .30 + .30 * _glow.value,
                                  ),
                                  blurRadius: 18 + 14 * _glow.value,
                                  spreadRadius: 2 + 4 * _glow.value,
                                ),
                              ]
                              : enabled
                              ? [
                                BoxShadow(
                                  color: palette.accent.withValues(alpha: .18),
                                  blurRadius: 18,
                                ),
                              ]
                              : null,
                    ),
                    child: child,
                  ),
                ),
            // Mic centred in the circle with the label directly under it; the
            // padding keeps a long label off the curved edge.
            child: Padding(
              padding: EdgeInsets.symmetric(horizontal: widget.diameter * .14),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    held ? Icons.mic : Icons.mic_none,
                    color: held ? palette.onTransmit : palette.accent,
                    size: widget.diameter * .22,
                  ),
                  SizedBox(height: widget.diameter * .04),
                  Text(
                    'TX',
                    key: const ValueKey('tx-ptt-mode'),
                    style: consoleState(
                      palette,
                      size: labelSize + 2,
                      color: ink,
                    ).copyWith(letterSpacing: 2),
                  ),
                  Text(
                    held
                        ? l10n.txReleaseToStop
                        : !enabled && widget.disabledText != null
                        ? widget.disabledText!
                        : l10n.txHoldToTalk,
                    textAlign: TextAlign.center,
                    style: consoleState(
                      palette,
                      size: labelSize,
                      color: ink,
                    ).copyWith(letterSpacing: 1),
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
