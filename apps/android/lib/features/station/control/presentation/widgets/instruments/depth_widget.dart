import 'package:prana_mobile/l10n/app_localizations.dart';
import 'package:flutter/material.dart';
import 'depth_scale.dart';
import 'instrument_value.dart';

class DepthWidget extends StatelessWidget {
  const DepthWidget({super.key, required this.value});
  final double? value;

  @override
  Widget build(BuildContext context) {
    return InstrumentValue(
      icon: Icons.vertical_align_bottom,
      label: AppLocalizations.of(context).depth,
      value: value?.toStringAsFixed(1) ?? '—',
      unit: 'M',
      // The track carries the change a delta chip would state, and in a strip
      // cell there is room for one of the two, not both.
      visual: DepthScale(metres: value, height: 10, labelled: false),
    );
  }
}
