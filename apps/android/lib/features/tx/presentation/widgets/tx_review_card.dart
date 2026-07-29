import 'package:flutter/material.dart';

import '../../../../core/localization.dart';
import '../../domain/tx_draft.dart';

class TxReviewCard extends StatelessWidget {
  const TxReviewCard({
    super.key,
    required this.draft,
    required this.languageLabel,
    required this.onTransmit,
    required this.onCancel,
  });

  final TxDraft draft;
  final String languageLabel;
  final VoidCallback onTransmit;
  final VoidCallback onCancel;

  @override
  Widget build(BuildContext context) => ListView(
    key: const ValueKey('tx-review-view'),
    padding: const EdgeInsets.fromLTRB(16, 14, 16, 24),
    children: [
      Row(
        children: [
          Expanded(
            child: Text(
              AppText.of(context, 'tx_review_title'),
              style: Theme.of(
                context,
              ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w900),
            ),
          ),
          Chip(
            avatar: const Icon(Icons.schedule, size: 16),
            label: Text(
              '${(draft.duration.inMilliseconds / 1000).toStringAsFixed(1)} s',
            ),
          ),
        ],
      ),
      const SizedBox(height: 14),
      _ReadOnlySection(
        title: AppText.of(context, 'tx_transcript'),
        value: draft.transcript,
      ),
      const SizedBox(height: 12),
      _ReadOnlySection(
        title: '${AppText.of(context, 'tx_translation')} · $languageLabel',
        value: draft.translation,
        highlighted: true,
      ),
      const SizedBox(height: 20),
      FilledButton.icon(
        key: const ValueKey('tx-confirm-button'),
        onPressed: onTransmit,
        icon: const Icon(Icons.send),
        label: Text(AppText.of(context, 'tx_transmit')),
      ),
      const SizedBox(height: 10),
      OutlinedButton(
        key: const ValueKey('tx-cancel-button'),
        onPressed: onCancel,
        child: Text(AppText.of(context, 'tx_cancel')),
      ),
    ],
  );
}

class _ReadOnlySection extends StatelessWidget {
  const _ReadOnlySection({
    required this.title,
    required this.value,
    this.highlighted = false,
  });

  final String title;
  final String value;
  final bool highlighted;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(
      color: highlighted ? const Color(0xFFEAF2FB) : Colors.white,
      borderRadius: BorderRadius.circular(14),
      border: Border.all(color: const Color(0xFFD4E2E5)),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: const TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w800,
            color: Color(0xFF607983),
          ),
        ),
        const SizedBox(height: 8),
        SelectableText(
          value,
          style: const TextStyle(fontSize: 16, height: 1.45),
        ),
      ],
    ),
  );
}
