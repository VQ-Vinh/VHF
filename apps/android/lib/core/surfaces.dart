import 'package:flutter/material.dart';

/// The panel every dashboard surface sits on.
///
/// One definition so instruments and the status block cannot drift apart. The
/// radius matches `cardTheme` in core/theme.dart; the shadow is deliberately
/// almost invisible, and absent in dark mode where it only muddies the
/// surface instead of lifting it.
BoxDecoration panelDecoration(BuildContext context) {
  final theme = Theme.of(context);
  final colors = theme.colorScheme;
  return BoxDecoration(
    color: colors.surface,
    border: Border.all(color: colors.outlineVariant),
    borderRadius: BorderRadius.circular(16),
    boxShadow:
        theme.brightness == Brightness.light
            ? [
              BoxShadow(
                color: colors.shadow.withValues(alpha: 0.05),
                blurRadius: 10,
                offset: const Offset(0, 2),
              ),
            ]
            : null,
  );
}

/// Small caps-ish heading used above and inside panels.
TextStyle? panelLabelStyle(BuildContext context) {
  final theme = Theme.of(context);
  return theme.textTheme.labelLarge?.copyWith(
    fontWeight: FontWeight.w700,
    letterSpacing: 0.6,
    color: theme.colorScheme.onSurfaceVariant,
  );
}
