import 'package:flutter/material.dart';

import '../../../../core/localization.dart';
import '../../domain/tx_draft.dart';

class TxReviewCard extends StatefulWidget {
  const TxReviewCard({
    super.key,
    required this.draft,
    required this.languageLabel,
    required this.onTransmit,
    required this.onCancel,
  });

  final TxDraft draft;
  final String languageLabel;
  final ValueChanged<String> onTransmit;
  final VoidCallback onCancel;

  @override
  State<TxReviewCard> createState() => _TxReviewCardState();
}

class _TxReviewCardState extends State<TxReviewCard> {
  late final TextEditingController translation;

  @override
  void initState() {
    super.initState();
    translation = TextEditingController(text: widget.draft.translation);
    translation.addListener(_refresh);
  }

  void _refresh() => setState(() {});

  @override
  void dispose() {
    translation
      ..removeListener(_refresh)
      ..dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final valid =
        translation.text.trim().isNotEmpty && translation.text.length <= 2000;
    return ListView(
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
                '${(widget.draft.duration.inMilliseconds / 1000).toStringAsFixed(1)} s',
              ),
            ),
          ],
        ),
        const SizedBox(height: 14),
        _ReadOnlySection(
          title: AppText.of(context, 'tx_transcript'),
          value: widget.draft.transcript,
        ),
        const SizedBox(height: 12),
        TextField(
          key: const ValueKey('tx-translation-editor'),
          controller: translation,
          maxLength: 2000,
          minLines: 4,
          maxLines: 8,
          decoration: InputDecoration(
            labelText:
                '${AppText.of(context, 'tx_translation')} · ${widget.languageLabel}',
            helperText: AppText.of(context, 'tx_translation_edit_hint'),
            alignLabelWithHint: true,
          ),
        ),
        const SizedBox(height: 12),
        FilledButton.icon(
          key: const ValueKey('tx-confirm-button'),
          onPressed:
              valid ? () => widget.onTransmit(translation.text.trim()) : null,
          icon: const Icon(Icons.send),
          label: Text(AppText.of(context, 'tx_transmit')),
        ),
        const SizedBox(height: 10),
        OutlinedButton(
          key: const ValueKey('tx-cancel-button'),
          onPressed: widget.onCancel,
          child: Text(AppText.of(context, 'tx_cancel')),
        ),
      ],
    );
  }
}

class _ReadOnlySection extends StatelessWidget {
  const _ReadOnlySection({required this.title, required this.value});

  final String title;
  final String value;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(
      color: Colors.white,
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
