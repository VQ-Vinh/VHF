import 'package:flutter/material.dart';

import 'theme.dart';

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
  Widget build(BuildContext context) => AppBar(
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
              Text(title, overflow: TextOverflow.ellipsis),
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
  const StatusPill({super.key, required this.label, required this.online});
  final String label;
  final bool online;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
    decoration: BoxDecoration(
      color: online ? const Color(0xFFDDF3E8) : const Color(0xFFE7EEF0),
      borderRadius: BorderRadius.circular(8),
    ),
    child: Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(
          Icons.circle,
          size: 8,
          color: online ? const Color(0xFF16704A) : PranaTheme.muted,
        ),
        const SizedBox(width: 6),
        Text(
          label.toUpperCase(),
          style: TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w800,
            color: online ? const Color(0xFF166440) : PranaTheme.muted,
          ),
        ),
      ],
    ),
  );
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
    child: Padding(
      padding: const EdgeInsets.all(32),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 52, color: PranaTheme.brandBlue),
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
              style: const TextStyle(color: PranaTheme.muted),
            ),
          ],
        ],
      ),
    ),
  );
}
