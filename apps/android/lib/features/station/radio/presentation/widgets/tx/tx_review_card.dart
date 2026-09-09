import 'package:prana_mobile/l10n/app_localizations.dart';
import 'package:flutter/material.dart';

import 'package:prana_mobile/domain/radio/tx/tx_draft.dart';

class TxReviewCard extends StatefulWidget {
  const TxReviewCard({
    super.key,
    required this.draft,
    required this.languageLabel,
    required this.onTransmit,
    required this.onCancel,
    this.initialTranslation,
    this.onChanged,
  });

  final String? initialTranslation;
  final ValueChanged<String>? onChanged;
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
    translation = TextEditingController(
      text: widget.initialTranslation ?? widget.draft.translation,
    );
    translation.addListener(_refresh);
  }

  void _refresh() {
    widget.onChanged?.call(translation.text);
    setState(() {});
  }

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
                AppLocalizations.of(context).txReviewTitle,
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
          title: AppLocalizations.of(context).txTranscript,
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
                '${AppLocalizations.of(context).txTranslation} · ${widget.languageLabel}',
            helperText: AppLocalizations.of(context).txTranslationEditHint,
            alignLabelWithHint: true,
          ),
        ),
        const SizedBox(height: 12),
        FilledButton.icon(
          key: const ValueKey('tx-confirm-button'),
          onPressed:
              valid ? () => widget.onTransmit(translation.text.trim()) : null,
          icon: const Icon(Icons.send),
          label: Text(AppLocalizations.of(context).txTransmit),
        ),
        const SizedBox(height: 10),
        OutlinedButton(
          key: const ValueKey('tx-cancel-button'),
          onPressed: widget.onCancel,
          child: Text(AppLocalizations.of(context).txCancel),
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
      color: Theme.of(context).colorScheme.surface,
      borderRadius: BorderRadius.circular(14),
      border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w800,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
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
