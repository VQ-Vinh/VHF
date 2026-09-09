import 'package:prana_mobile/l10n/app_localizations.dart';
import 'package:flutter/material.dart';
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
      unit: 'm',
    );
  }
}
