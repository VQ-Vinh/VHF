import 'package:prana_mobile/l10n/app_localizations.dart';
import 'package:flutter/material.dart';
import 'instrument_value.dart';

class HeadingWidget extends StatelessWidget {
  const HeadingWidget({super.key, required this.value});
  final double? value;

  /// The eight-point name of a bearing.
  static String compassPoint(double degrees) {
    const points = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
    return points[((degrees % 360) / 45).round() % 8];
  }

  @override
  Widget build(BuildContext context) {
    final degrees = value;
    return InstrumentValue(
      icon: Icons.explore_outlined,
      label: AppLocalizations.of(context).heading,
      // Three digits, as a bearing is spoken and written: 034, not 34.
      value: degrees?.round().toString().padLeft(3, '0') ?? '—',
      unit: '°',
      // The point only; nothing here knows whether the heading is true or
      // magnetic, so the cell does not claim a reference.
      extra:
          degrees == null ? null : InstrumentChip(label: compassPoint(degrees)),
    );
  }
}
