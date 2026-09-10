import 'package:prana_mobile/l10n/app_localizations.dart';
import 'package:flutter/material.dart';
import 'depth_scale.dart';
import 'instrument_value.dart';
import 'telemetry_delta.dart';

class DepthWidget extends StatelessWidget {
  const DepthWidget({super.key, required this.value, this.delta});
  final double? value;
  final double? delta;

  @override
  Widget build(BuildContext context) {
    return InstrumentValue(
      icon: Icons.vertical_align_bottom,
      label: AppLocalizations.of(context).depth,
      value: value?.toStringAsFixed(1) ?? '—',
      unit: 'M',
      delta:
          delta == null
              ? null
              : TelemetryDelta(value: delta!, unit: 'm', fractionDigits: 2),
      visual: DepthScale(metres: value),
    );
  }
}
