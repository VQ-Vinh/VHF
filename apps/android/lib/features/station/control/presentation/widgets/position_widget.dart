import 'package:prana_mobile/l10n/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:prana_mobile/telemetry/domain/telemetry_repository.dart';

class PositionWidget extends StatelessWidget {
  const PositionWidget({
    super.key,
    required this.position,
    this.showSource = true,
  });
  final TelemetryPosition? position;
  final bool showSource;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 12),
    child: Wrap(
      spacing: 12,
      runSpacing: 8,
      children: [
        ExcludeSemantics(
          child: Icon(
            Icons.location_on_outlined,
            color: Theme.of(context).colorScheme.primary,
            size: 24,
          ),
        ),
        Text(
          AppLocalizations.of(context).position,
          style: const TextStyle(fontWeight: FontWeight.w700),
        ),
        Text(
          position == null
              ? '—'
              : '${position!.latitude.toStringAsFixed(5)}, ${position!.longitude.toStringAsFixed(5)}',
        ),
        if (showSource)
          Text(
            AppLocalizations.of(context).telemetryMock,
            style: TextStyle(
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
      ],
    ),
  );
}
