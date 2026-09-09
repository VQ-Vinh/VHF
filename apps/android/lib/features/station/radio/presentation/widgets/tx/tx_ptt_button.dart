import 'package:prana_mobile/l10n/app_localizations.dart';
import 'package:flutter/material.dart';

import 'package:prana_mobile/core/theme.dart';

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
  late final AnimationController _pulseController;
  late final Animation<double> _pulse;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 850),
    );
    _pulse = Tween<double>(begin: 1, end: 1.08).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _syncPulse();
  }

  @override
  void didUpdateWidget(covariant TxPttButton oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.recording != widget.recording) _syncPulse();
  }

  void _syncPulse() {
    final reduceMotion =
        MediaQuery.maybeOf(context)?.disableAnimations ?? false;
    if (widget.recording && !reduceMotion) {
      if (!_pulseController.isAnimating) {
        _pulseController.repeat(reverse: true);
      }
    } else {
      _pulseController.stop();
      _pulseController.value = 0;
    }
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final color =
        widget.recording ? const Color(0xFFC33F4F) : PranaTheme.brandBlue;
    return Semantics(
      button: true,
      enabled: widget.enabled,
      liveRegion: widget.recording,
      label:
          (widget.recording
              ? AppLocalizations.of(context).txRecording
              : AppLocalizations.of(context).txHoldToTalk),
      hint: AppLocalizations.of(
        context,
      ).txMaxDuration(widget.maximumSeconds.toString()),
      child: Listener(
        key: const ValueKey('tx-ptt-button'),
        onPointerDown: widget.enabled ? (_) => widget.onHoldStart() : null,
        onPointerUp:
            widget.enabled || widget.recording
                ? (_) => widget.onHoldEnd()
                : null,
        onPointerCancel:
            widget.enabled || widget.recording
                ? (_) => widget.onHoldEnd()
                : null,
        child: ScaleTransition(
          scale: _pulse,
          // Resize the constraints immediately; only decoration animates. An
          // interpolated diameter can briefly clip newly scaled text on resize.
          child: SizedBox(
            width: widget.diameter,
            height: widget.diameter,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 160),
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: widget.enabled ? color : const Color(0xFFB8C7CB),
                border: Border.all(
                  color:
                      widget.enabled
                          ? color.withValues(alpha: .22)
                          : Colors.white,
                  width: 10,
                ),
                boxShadow:
                    widget.enabled
                        ? [
                          BoxShadow(
                            color: color.withValues(alpha: .2),
                            blurRadius: widget.recording ? 14 : 24,
                            spreadRadius: widget.recording ? 4 : 5,
                          ),
                        ]
                        : null,
              ),
              // Mic centred in the circle with the label directly under it; the
              // padding keeps a long label off the curved edge.
              child: Padding(
                padding: EdgeInsets.symmetric(
                  horizontal: widget.diameter * .12,
                ),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      widget.recording ? Icons.mic : Icons.mic_none,
                      color: Colors.white,
                      size: widget.diameter * .26,
                    ),
                    SizedBox(height: widget.diameter * .05),
                    Text(
                      widget.recording
                          ? AppLocalizations.of(context).txReleaseToStop
                          : !widget.enabled && widget.disabledText != null
                          ? widget.disabledText!
                          : AppLocalizations.of(context).txHoldToTalk,
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: (widget.diameter * .085).clamp(11, 15),
                        fontWeight: FontWeight.w900,
                        letterSpacing: .4,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
