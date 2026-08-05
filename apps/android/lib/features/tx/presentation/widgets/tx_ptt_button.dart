import 'package:flutter/material.dart';

import '../../../../core/localization.dart';
import '../../../../core/theme.dart';

class TxPttButton extends StatelessWidget {
  const TxPttButton({
    super.key,
    required this.enabled,
    required this.recording,
    required this.onHoldStart,
    required this.onHoldEnd,
    this.compact = false,
    this.disabledTextKey,
  });

  final bool enabled;
  final bool recording;
  final VoidCallback onHoldStart;
  final VoidCallback onHoldEnd;
  final bool compact;
  final String? disabledTextKey;

  @override
  Widget build(BuildContext context) {
    final color = recording ? const Color(0xFFC33F4F) : PranaTheme.brandBlue;
    return Semantics(
      button: true,
      enabled: enabled,
      label: AppText.of(context, 'tx_hold_to_talk'),
      child: Listener(
        key: const ValueKey('tx-ptt-button'),
        onPointerDown: enabled ? (_) => onHoldStart() : null,
        onPointerUp: enabled || recording ? (_) => onHoldEnd() : null,
        onPointerCancel: enabled || recording ? (_) => onHoldEnd() : null,
        child: AnimatedScale(
          scale: recording ? .96 : 1,
          duration: const Duration(milliseconds: 120),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 160),
            width: compact ? 112 : 172,
            height: compact ? 64 : 172,
            decoration: BoxDecoration(
              shape: compact ? BoxShape.rectangle : BoxShape.circle,
              borderRadius: compact ? BorderRadius.circular(10) : null,
              color: enabled ? color : const Color(0xFFB8C7CB),
              border: Border.all(
                color: enabled ? color.withValues(alpha: .22) : Colors.white,
                width: compact ? 2 : 12,
              ),
              boxShadow:
                  enabled
                      ? [
                        BoxShadow(
                          color: color.withValues(alpha: .2),
                          blurRadius: recording ? 10 : 24,
                          spreadRadius: recording ? 2 : 5,
                        ),
                      ]
                      : null,
            ),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  recording ? Icons.mic : Icons.mic_none,
                  color: Colors.white,
                  size: compact ? 20 : 42,
                ),
                SizedBox(height: compact ? 3 : 8),
                Text(
                  AppText.of(
                    context,
                    recording
                        ? 'tx_release_to_stop'
                        : !enabled && disabledTextKey != null
                        ? disabledTextKey!
                        : 'tx_hold_to_talk',
                  ),
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: compact ? 9 : 13,
                    fontWeight: FontWeight.w900,
                    letterSpacing: .4,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
