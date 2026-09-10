import 'package:prana_mobile/l10n/app_localizations.dart';
import 'package:flutter/material.dart';
import 'instrument_value.dart';
import 'speed_trend.dart';
import 'telemetry_delta.dart';

class SpeedWidget extends StatelessWidget {
  const SpeedWidget({
    super.key,
    required this.value,
    this.delta,
    this.history = const [],
  });
  final double? value;
  final double? delta;
  final List<double> history;

  @override
  Widget build(BuildContext context) {
    return InstrumentValue(
      icon: Icons.speed,
      label: AppLocalizations.of(context).speed,
      value: value?.toStringAsFixed(1) ?? '—',
      unit: 'KT',
      delta: delta == null ? null : TelemetryDelta(value: delta!, unit: 'kt'),
      visual: history.length < 2 ? null : SpeedTrend(values: history),
    );
  }
}
