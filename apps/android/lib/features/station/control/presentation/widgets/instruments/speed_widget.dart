import 'package:prana_mobile/l10n/app_localizations.dart';
import 'package:flutter/material.dart';
import 'instrument_value.dart';
import 'telemetry_delta.dart';

class SpeedWidget extends StatelessWidget {
  const SpeedWidget({super.key, required this.value, this.delta});
  final double? value;
  final double? delta;

  @override
  Widget build(BuildContext context) {
    return InstrumentValue(
      icon: Icons.speed,
      label: AppLocalizations.of(context).speed,
      value: value?.toStringAsFixed(1) ?? '—',
      unit: 'KT',
      extra: delta == null ? null : TelemetryDelta(value: delta!, unit: 'kt'),
    );
  }
}
