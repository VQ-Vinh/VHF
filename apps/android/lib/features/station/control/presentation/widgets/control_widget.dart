import 'package:prana_mobile/l10n/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:prana_mobile/core/responsive.dart';
import 'package:prana_mobile/core/surfaces.dart';
import '../../application/steering_state.dart';
import 'sim_notice.dart';

class ControlWidget extends StatelessWidget {
  const ControlWidget({super.key, required this.mode, required this.onChanged});
  final MockControlMode mode;
  final ValueChanged<MockControlMode> onChanged;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 10),
          child: Text(l10n.control, style: panelLabelStyle(context)),
        ),
        // Side by side while both labels fit, stacked once the text scale says
        // they no longer do. Two full-width targets read as one switch either
        // way, which a pair of chips floating in a Wrap never did.
        AdaptiveFields(
          minimumWidth: 120,
          gap: 10,
          children: [
            for (final value in MockControlMode.values)
              _ModeButton(
                icon:
                    value == MockControlMode.auto
                        ? Icons.autorenew
                        : Icons.pan_tool_alt_outlined,
                label: value == MockControlMode.auto ? l10n.auto : l10n.manual,
                selected: mode == value,
                onPressed: () => onChanged(value),
              ),
          ],
        ),
        const SizedBox(height: 12),
        SimNotice(icon: Icons.link_off, message: l10n.controlMock),
      ],
    );
  }
}

class _ModeButton extends StatelessWidget {
  const _ModeButton({
    required this.icon,
    required this.label,
    required this.selected,
    required this.onPressed,
  });
  final IconData icon;
  final String label;
  final bool selected;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    final foreground = selected ? colors.onPrimary : colors.onSurfaceVariant;
    return Semantics(
      selected: selected,
      button: true,
      child: Material(
        color: selected ? colors.primary : colors.surface,
        borderRadius: BorderRadius.circular(12),
        child: InkWell(
          borderRadius: BorderRadius.circular(12),
          onTap: onPressed,
          child: Container(
            constraints: const BoxConstraints(minHeight: 48),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: selected ? colors.primary : colors.outlineVariant,
              ),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(icon, size: 18, color: foreground),
                const SizedBox(width: 8),
                // Flexible so a long label wraps to a second line instead of
                // pushing the row wider than the column it sits in.
                Flexible(
                  child: Text(
                    label,
                    textAlign: TextAlign.center,
                    style: theme.textTheme.labelLarge?.copyWith(
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.3,
                      color: foreground,
                    ),
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
