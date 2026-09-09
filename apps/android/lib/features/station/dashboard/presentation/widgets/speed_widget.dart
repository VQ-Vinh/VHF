import 'package:prana_mobile/l10n/app_localizations.dart';
import 'package:flutter/material.dart';
import 'instrument_value.dart';

class SpeedWidget extends StatelessWidget {
  const SpeedWidget({super.key, required this.value});
  final double? value;
  @override
  Widget build(BuildContext context) {
    return InstrumentValue(
      icon: Icons.speed,
      label: AppLocalizations.of(context).speed,
      value: value?.toStringAsFixed(1) ?? '—',
      unit: 'kt',
    );
  }
}
