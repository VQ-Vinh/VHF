import 'package:prana_mobile/l10n/app_localizations.dart';
import 'package:flutter/material.dart';
import 'compass_rose.dart';
import 'instrument_value.dart';

class HeadingWidget extends StatelessWidget {
  const HeadingWidget({super.key, required this.value});
  final double? value;

  @override
  Widget build(BuildContext context) {
    final directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
    return InstrumentValue(
      icon: Icons.explore_outlined,
      label: AppLocalizations.of(context).heading,
      value: value?.toStringAsFixed(0) ?? '—',
      unit:
          value == null
              ? '—'
              : '°  ${directions[((value! % 360) / 45).round() % 8]}',
      trailing: CompassRose(degrees: value),
    );
  }
}
