import 'package:flutter/material.dart';

import 'depth_widget.dart';
import 'heading_widget.dart';
import 'speed_widget.dart';

/// Speed, depth and heading across the top of Control.
///
/// These three used to be the Dashboard tab. They sit above the chart because
/// they are what a helmsman reads while steering, so they stay put while the
/// rest of the tab scrolls -- as long as they fit on one row. [fitsOneRow] is
/// what the tab asks before pinning them: stacked, they are too tall to hold a
/// third of a short screen.
class InstrumentStrip extends StatelessWidget {
  const InstrumentStrip({
    super.key,
    required this.speedKnots,
    required this.speedDelta,
    required this.depthMetres,
    required this.headingDegrees,
  });

  final double? speedKnots;
  final double? speedDelta;
  final double? depthMetres;
  final double? headingDegrees;

  static const double _minimumCell = 88;
  static const double _gap = 10;

  /// Whether three cells fit side by side in [width] at this text scale.
  /// The tab asks this too, before deciding whether to pin the strip.
  static bool fitsOneRow(BuildContext context, double width) =>
      width >=
      MediaQuery.textScalerOf(context).scale(_minimumCell) * 3 + _gap * 2;

  @override
  Widget build(BuildContext context) {
    final cells = <Widget>[
      SpeedWidget(value: speedKnots, delta: speedDelta),
      DepthWidget(value: depthMetres),
      HeadingWidget(value: headingDegrees),
    ];
    return LayoutBuilder(
      builder: (context, constraints) {
        if (!fitsOneRow(context, constraints.maxWidth)) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            mainAxisSize: MainAxisSize.min,
            children: [
              for (var i = 0; i < cells.length; i++) ...[
                if (i > 0) const SizedBox(height: _gap),
                cells[i],
              ],
            ],
          );
        }
        // Three cells of one size: Expanded for equal widths against readings
        // of different lengths, and IntrinsicHeight with a stretched row for
        // equal heights against a chip in one cell and a depth track in
        // another. AdaptiveFields would leave each cell its own size, which
        // is right for a form and wrong for a row of instruments.
        return IntrinsicHeight(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              for (var i = 0; i < cells.length; i++) ...[
                if (i > 0) const SizedBox(width: _gap),
                Expanded(child: cells[i]),
              ],
            ],
          ),
        );
      },
    );
  }
}
