import 'responsive.dart';
import 'theme.dart';
import 'package:flutter/material.dart';

class PranaLogo extends StatelessWidget {
  const PranaLogo.mark({super.key, this.size = 52, this.color})
    : lockup = false;

  const PranaLogo.lockup({super.key, this.size = 156})
    : lockup = true,
      color = null;

  final double size;
  final bool lockup;
  final Color? color;

  @override
  Widget build(BuildContext context) => Image.asset(
    lockup ? 'assets/logo_lockup.png' : 'assets/logo_mark.png',
    key: ValueKey(lockup ? 'prana-logo-lockup' : 'prana-logo-mark'),
    width: size,
    height: lockup ? size * .72 : size,
    fit: BoxFit.contain,
    filterQuality: FilterQuality.high,
    color: color,
    colorBlendMode: color == null ? null : BlendMode.srcIn,
  );
}

class PranaPageHeader extends StatelessWidget implements PreferredSizeWidget {
  const PranaPageHeader({
    super.key,
    required this.title,
    this.subtitle,
    this.actions,
  });
  final String title;
  final String? subtitle;
  final List<Widget>? actions;

  @override
  Size get preferredSize => const Size.fromHeight(70);

  @override
  Widget build(BuildContext context) => ResponsiveHeader(
    titleSpacing: 16,
    title: Row(
      children: [
        const PranaLogo.mark(size: 38, color: Colors.white),
        const SizedBox(width: 12),
        Flexible(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(title),
              if (subtitle != null)
                Text(
                  subtitle!,
                  style: const TextStyle(
                    fontSize: 11,
                    color: Color(0xFFA9C5CC),
                  ),
                ),
            ],
          ),
        ),
      ],
    ),
    actions: actions,
  );
}

class StatusPill extends StatelessWidget {
  const StatusPill({super.key, required this.label, required this.online})
    : onDark = false;

  /// For the navy header bar, where the light-surface palette would put a
  /// near-white block on dark chrome and shout louder than the title.
  const StatusPill.onDark({
    super.key,
    required this.label,
    required this.online,
  }) : onDark = true;

  final String label;
  final bool online;
  final bool onDark;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final background =
        onDark
            ? Colors.white.withValues(alpha: 0.10)
            : online
            // Brand blue, not the seed's tertiary: tertiaryContainer resolves
            // mauve in both themes, which reads as another product.
            ? colors.primaryContainer
            : colors.surfaceContainerHighest;
    final foreground =
        onDark
            ? const Color(0xFFA9C5CC)
            : online
            ? colors.onPrimaryContainer
            : colors.onSurfaceVariant;
    // On navy the dot carries the state on its own, so it keeps its colour
    // while the label stays the header's muted tone.
    final dot =
        onDark
            ? (online ? PranaTheme.brandBlueBright : const Color(0xFF7C93A3))
            : foreground;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.circle, size: 8, color: dot),
          const SizedBox(width: 6),
          // Flexible, not a plain Text: at text scale 2.0 a label such as
          // "STATION ONLINE" is wider than a narrow card, and an unconstrained
          // Row would overflow rather than wrap.
          Flexible(
            child: Text(
              label.toUpperCase(),
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w800,
                color: foreground,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class EmptyState extends StatelessWidget {
  const EmptyState({
    super.key,
    required this.icon,
    required this.title,
    this.subtitle,
  });
  final IconData icon;
  final String title;
  final String? subtitle;

  @override
  Widget build(BuildContext context) => Center(
    child: SingleChildScrollView(
      padding: const EdgeInsets.all(32),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 52, color: Theme.of(context).colorScheme.primary),
          const SizedBox(height: 16),
          Text(
            title,
            textAlign: TextAlign.center,
            style: Theme.of(
              context,
            ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
          ),
          if (subtitle != null) ...[
            const SizedBox(height: 8),
            Text(
              subtitle!,
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ],
      ),
    ),
  );
}
