import 'package:flutter/material.dart';

abstract final class ContentWidth {
  static const auth = 440.0;
  static const form = 720.0;
  static const reading = 1120.0;
  static const dashboard = 1440.0;
}

/// Constrains content without changing its height or its scroll owner.
class ContentFrame extends StatelessWidget {
  const ContentFrame({
    super.key,
    required this.child,
    this.maxWidth = ContentWidth.reading,
  });
  final Widget child;
  final double maxWidth;
  @override
  Widget build(BuildContext context) => Align(
    alignment: Alignment.topCenter,
    heightFactor: 1,
    child: ConstrainedBox(
      constraints: BoxConstraints(maxWidth: maxWidth),
      child: SizedBox(width: double.infinity, child: child),
    ),
  );
}

/// Natural-height headers avoid the fixed PreferredSize contract of AppBar.
class ResponsiveScaffold extends StatelessWidget {
  const ResponsiveScaffold({
    super.key,
    this.appBar,
    this.body,
    this.bottomNavigationBar,
    this.floatingActionButton,
    this.maxWidth = ContentWidth.reading,
  });
  final Widget? appBar, body, bottomNavigationBar, floatingActionButton;
  final double maxWidth;
  @override
  Widget build(BuildContext context) => Scaffold(
    floatingActionButton: floatingActionButton,
    body: SafeArea(
      child: Column(
        children: [
          if (appBar != null) appBar!,
          Expanded(
            child: ContentFrame(
              maxWidth: maxWidth,
              child: body ?? const SizedBox.shrink(),
            ),
          ),
          if (bottomNavigationBar != null)
            ContentFrame(maxWidth: maxWidth, child: bottomNavigationBar!),
        ],
      ),
    ),
  );
}

class ResponsiveHeader extends StatelessWidget {
  const ResponsiveHeader({
    super.key,
    this.title,
    this.leading,
    this.actions,
    this.automaticallyImplyLeading = true,
    this.toolbarHeight = 56,
    this.titleSpacing = 16,
    this.leadingWidth = 48,
    this.stackActions = false,
  });
  final Widget? title, leading;
  final List<Widget>? actions;
  final bool automaticallyImplyLeading, stackActions;
  final double toolbarHeight, titleSpacing, leadingWidth;
  @override
  Widget build(BuildContext context) {
    final back =
        leading ??
        (automaticallyImplyLeading && Navigator.of(context).canPop()
            ? const BackButton()
            : null);
    return Material(
      color: Theme.of(context).appBarTheme.backgroundColor,
      child: IconTheme(
        data: const IconThemeData(color: Colors.white),
        child: DefaultTextStyle(
          style: Theme.of(
            context,
          ).textTheme.titleLarge!.copyWith(color: Colors.white),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                ConstrainedBox(
                  constraints: BoxConstraints(minHeight: toolbarHeight - 16),
                  child: Row(
                    children: [
                      if (back != null)
                        SizedBox(width: leadingWidth, child: back),
                      SizedBox(width: titleSpacing),
                      Expanded(child: title ?? const SizedBox.shrink()),
                      if (!stackActions) ...?actions,
                    ],
                  ),
                ),
                if (stackActions && actions != null)
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    alignment: WrapAlignment.end,
                    children: actions!,
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Uses a stable Flex parent when fields change between a row and a column.
class AdaptiveFields extends StatelessWidget {
  const AdaptiveFields({
    super.key,
    required this.children,
    this.minimumWidth = 160,
    this.gap = 12,
  });
  final List<Widget> children;
  final double minimumWidth, gap;
  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final vertical =
          constraints.maxWidth <
          MediaQuery.textScalerOf(context).scale(minimumWidth) *
                  children.length +
              gap * (children.length - 1);
      return Flex(
        direction: vertical ? Axis.vertical : Axis.horizontal,
        crossAxisAlignment:
            vertical ? CrossAxisAlignment.stretch : CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          for (var i = 0; i < children.length; i++) ...[
            if (i > 0)
              SizedBox(width: vertical ? 0 : gap, height: vertical ? gap : 0),
            Flexible(flex: vertical ? 0 : 1, child: children[i]),
          ],
        ],
      );
    },
  );
}
