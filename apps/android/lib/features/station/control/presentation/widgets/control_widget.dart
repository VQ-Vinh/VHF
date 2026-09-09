import 'package:prana_mobile/l10n/app_localizations.dart';
import 'package:flutter/material.dart';
import '../../application/steering_state.dart';

class ControlWidget extends StatelessWidget {
  const ControlWidget({super.key, required this.mode, required this.onChanged});
  final MockControlMode mode;
  final ValueChanged<MockControlMode> onChanged;
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      Text(
        AppLocalizations.of(context).control,
        style: Theme.of(context).textTheme.titleMedium,
      ),
      const SizedBox(height: 12),
      Wrap(
        spacing: 8,
        runSpacing: 8,
        children: [
          for (final value in MockControlMode.values)
            ChoiceChip(
              label: Text(
                (value == MockControlMode.auto
                    ? AppLocalizations.of(context).auto
                    : AppLocalizations.of(context).manual),
              ),
              selected: mode == value,
              onSelected: (_) => onChanged(value),
              materialTapTargetSize: MaterialTapTargetSize.padded,
            ),
        ],
      ),
      const SizedBox(height: 8),
      Text(
        AppLocalizations.of(context).controlMock,
        style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant),
      ),
    ],
  );
}
