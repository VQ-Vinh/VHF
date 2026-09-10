import 'package:flutter/material.dart';

/// A standing caution about the simulation, not a transient error.
///
/// Amber rather than the theme's error red: nothing has gone wrong, the panel
/// simply is not a navigation instrument, and colouring it as a fault would
/// teach the crew to ignore real faults.
class SimNotice extends StatelessWidget {
  const SimNotice({super.key, required this.icon, required this.message});
  final IconData icon;
  final String message;

  static Color _amber(Brightness brightness) =>
      brightness == Brightness.dark
          ? const Color(0xFFE3B341)
          : const Color(0xFF9A6400);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final tone = _amber(theme.brightness);
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
      decoration: BoxDecoration(
        color: tone.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(10),
        border: Border(left: BorderSide(color: tone, width: 3)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 16, color: tone),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              message,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
                height: 1.35,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
