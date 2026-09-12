import 'package:flutter/material.dart';
import 'package:prana_mobile/core/responsive.dart';

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
  /// Mirrors what [AdaptiveFields] decides with the same numbers.
  static bool fitsOneRow(BuildContext context, double width) =>
      width >=
      MediaQuery.textScalerOf(context).scale(_minimumCell) * 3 + _gap * 2;

  @override
  Widget build(BuildContext context) => AdaptiveFields(
    minimumWidth: _minimumCell,
    gap: _gap,
    children: [
      SpeedWidget(value: speedKnots, delta: speedDelta),
      DepthWidget(value: depthMetres),
      HeadingWidget(value: headingDegrees),
    ],
  );
}
