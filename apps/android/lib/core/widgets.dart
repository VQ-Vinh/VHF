import 'responsive.dart';
import 'theme.dart';
import 'package:flutter/material.dart';

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

enum NoticeTone { error, info, success }

/// Inline feedback box for forms and pages. Colours come from the colour
/// scheme so it reads in light and dark mode; the text wraps instead of
/// clipping, and actions wrap onto a new line on narrow screens.
class NoticeCard extends StatelessWidget {
  const NoticeCard({
    super.key,
    required this.message,
    this.tone = NoticeTone.error,
    this.actions = const [],
    this.margin = const EdgeInsets.only(top: 14),
  });

  final String message;
  final NoticeTone tone;
  final List<Widget> actions;
  final EdgeInsetsGeometry margin;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    final (background, foreground, icon) = switch (tone) {
      NoticeTone.error => (
        colors.errorContainer,
        colors.onErrorContainer,
        Icons.error_outline,
      ),
      NoticeTone.info => (
        colors.secondaryContainer,
        colors.onSecondaryContainer,
        Icons.info_outline,
      ),
      // The scheme has no success role; these pairs keep AA contrast.
      NoticeTone.success => (
        theme.brightness == Brightness.light
            ? const Color(0xFFDDF3E6)
            : const Color(0xFF173A2B),
        theme.brightness == Brightness.light
            ? const Color(0xFF1F5E43)
            : const Color(0xFFB7E8CB),
        Icons.check_circle_outline,
      ),
    };
    // The icon grows with the text so it stays level with the first line.
    final iconSize = MediaQuery.textScalerOf(context).scale(20).clamp(20, 32);
    return Semantics(
      container: true,
      liveRegion: true,
      child: Container(
        width: double.infinity,
        margin: margin,
        padding: EdgeInsets.fromLTRB(12, 12, 12, actions.isEmpty ? 12 : 4),
        decoration: BoxDecoration(
          color: background,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Padding(
                  padding: const EdgeInsets.only(top: 1),
                  child: Icon(
                    icon,
                    size: iconSize.toDouble(),
                    color: foreground,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    message,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: foreground,
                      height: 1.35,
                    ),
                  ),
                ),
              ],
            ),
            if (actions.isNotEmpty)
              TextButtonTheme(
                data: TextButtonThemeData(
                  style: TextButton.styleFrom(
                    foregroundColor: foreground,
                    minimumSize: const Size(48, 48),
                  ),
                ),
                child: Wrap(
                  alignment: WrapAlignment.end,
                  spacing: 4,
                  children: actions,
                ),
              ),
          ],
        ),
      ),
    );
  }
}

/// Full-area state for content that failed to load. Width stays readable on
/// tablets, and it scrolls rather than overflowing on short landscape screens.
class ErrorState extends StatelessWidget {
  const ErrorState({
    super.key,
    required this.title,
    required this.message,
    this.onRetry,
    this.retryLabel,
    this.retryKey,
    this.icon = Icons.cloud_off_outlined,
  });

  final String title;
  final String message;
  final VoidCallback? onRetry;
  final String? retryLabel;
  final Key? retryKey;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: ContentWidth.auth),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              DecoratedBox(
                decoration: BoxDecoration(
                  color: colors.errorContainer,
                  shape: BoxShape.circle,
                ),
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Icon(icon, size: 32, color: colors.onErrorContainer),
                ),
              ),
              const SizedBox(height: 16),
              Text(
                title,
                textAlign: TextAlign.center,
                style: theme.textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                message,
                textAlign: TextAlign.center,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: colors.onSurfaceVariant,
                  height: 1.4,
                ),
              ),
              if (onRetry != null && retryLabel != null) ...[
                const SizedBox(height: 20),
                FilledButton.icon(
                  key: retryKey,
                  onPressed: onRetry,
                  icon: const Icon(Icons.refresh),
                  label: Text(retryLabel!),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
