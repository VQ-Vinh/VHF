import 'dart:io';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

import '../../core/localization.dart';
import '../../core/widgets.dart';
import '../../models/plan_entitlements.dart';
import '../../models/station.dart';
import '../../providers.dart';

class HistoryScreen extends ConsumerStatefulWidget {
  const HistoryScreen({
    super.key,
    required this.stationId,
    this.embedded = false,
    this.onSessionSelected,
  });

  final String stationId;
  final bool embedded;
  final ValueChanged<String>? onSessionSelected;

  @override
  ConsumerState<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends ConsumerState<HistoryScreen> {
  String? selectedSession;

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(authStateProvider).value;
    final entitlements = ref.watch(planEntitlementsProvider);
    if (user == null) return const SizedBox.shrink();
    if (selectedSession != null) {
      return _SessionHistory(
        stationId: widget.stationId,
        sessionId: selectedSession!,
        entitlements: entitlements,
        onBack: () => setState(() => selectedSession = null),
      );
    }
    final stream =
        ref
            .watch(firestoreProvider)
            .collection('users')
            .doc(user.uid)
            .collection('stations')
            .doc(widget.stationId)
            .collection('sessions')
            .orderBy('updated_at', descending: true)
            .snapshots();
    return Scaffold(
      appBar: AppBar(
        automaticallyImplyLeading: !widget.embedded,
        title: Text(AppText.of(context, 'history')),
        actions: [
          if (widget.embedded)
            IconButton(
              onPressed: () => Navigator.of(context).pop(),
              icon: const Icon(Icons.close),
            ),
        ],
      ),
      body: StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
        stream: stream,
        builder: (context, snapshot) {
          if (snapshot.hasError) {
            return Center(child: Text('${snapshot.error}'));
          }
          if (!snapshot.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.data!.docs.isEmpty) {
            return EmptyState(
              icon: Icons.history,
              title: AppText.of(context, 'no_sessions'),
              subtitle: AppText.of(context, 'no_sessions_body'),
            );
          }
          return ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: snapshot.data!.docs.length,
            separatorBuilder: (_, _) => const SizedBox(height: 10),
            itemBuilder: (_, index) {
              final doc = snapshot.data!.docs[index];
              final updated =
                  (doc.data()['updated_at'] as Timestamp?)?.toDate();
              final locked =
                  updated != null &&
                  !entitlements.historyIsUnlocked(updated, DateTime.now());
              return Card(
                child: ListTile(
                  leading: const Icon(Icons.translate),
                  title: Text(doc.id),
                  subtitle: Text(
                    updated == null
                        ? AppText.of(context, 'syncing')
                        : DateFormat.yMMMd().add_Hm().format(updated),
                  ),
                  trailing: Icon(
                    locked ? Icons.lock_clock_outlined : Icons.chevron_right,
                  ),
                  onTap: () => setState(() => selectedSession = doc.id),
                ),
              );
            },
          );
        },
      ),
    );
  }
}

class _SessionHistory extends ConsumerStatefulWidget {
  const _SessionHistory({
    required this.stationId,
    required this.sessionId,
    required this.entitlements,
    required this.onBack,
  });
  final String stationId;
  final String sessionId;
  final PlanEntitlements entitlements;
  final VoidCallback onBack;

  @override
  ConsumerState<_SessionHistory> createState() => _SessionHistoryState();
}

class _SessionHistoryState extends ConsumerState<_SessionHistory> {
  final search = TextEditingController();
  final hidden = <String>{};
  late Future<List<TranslationResult>> results;
  String query = '';

  @override
  void initState() {
    super.initState();
    results = ref.read(apiProvider).stationResults(
      widget.stationId,
      widget.sessionId,
    );
  }

  @override
  void dispose() {
    search.dispose();
    super.dispose();
  }

  Future<void> _export(List<TranslationResult> items, bool csv) async {
    final directory = await getTemporaryDirectory();
    final extension = csv ? 'csv' : 'txt';
    final file = File('${directory.path}/prana-${widget.sessionId}.$extension');
    final text =
        csv
            ? [
              'time,language,transcript,translation',
              ...items.map(
                (item) => [
                  item.timestamp.toIso8601String(),
                  item.language,
                  item.transcript,
                  item.translation,
                ].map((value) => '"${value.replaceAll('"', '""')}"').join(','),
              ),
            ].join('\n')
            : items
                .map(
                  (item) =>
                      '[${DateFormat.Hms().format(item.timestamp)}] '
                      '[${item.language.toUpperCase()}]\n'
                      'TXT: ${item.transcript}\nTRN: ${item.translation}\n',
                )
                .join('\n');
    await file.writeAsString(text);
    await SharePlus.instance.share(
      ShareParams(files: [XFile(file.path)], title: widget.sessionId),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          onPressed: widget.onBack,
          icon: const Icon(Icons.arrow_back),
        ),
        title: Text(widget.sessionId),
      ),
      body: FutureBuilder<List<TranslationResult>>(
        future: results,
        builder: (context, snapshot) {
          if (snapshot.hasError) {
            return Center(child: Text('${snapshot.error}'));
          }
          if (!snapshot.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          final entitled = snapshot.data!;
          final all =
              entitled
                  .where((item) => !hidden.contains(item.requestId))
                  .toList();
          final filtered =
              all.where((item) {
                final text =
                    '${item.transcript} ${item.translation}'.toLowerCase();
                return text.contains(query.toLowerCase());
              }).toList();
          return Column(
            children: [
              if (widget.entitlements.historyUnlockDelayDays > 0)
                Container(
                  width: double.infinity,
                  color: const Color(0xFFFFF3D8),
                  padding: const EdgeInsets.fromLTRB(14, 10, 14, 10),
                  child: Text(
                    AppText.format(context, 'history_restricted', {
                      'days': widget.entitlements.historyUnlockDelayDays,
                    }),
                  ),
                ),
              Padding(
                padding: const EdgeInsets.all(12),
                child: TextField(
                  controller: search,
                  onChanged: (value) => setState(() => query = value),
                  decoration: InputDecoration(
                    hintText: AppText.of(context, 'history_search'),
                    prefixIcon: const Icon(Icons.search),
                  ),
                ),
              ),
              Wrap(
                spacing: 8,
                children: [
                  OutlinedButton(
                    onPressed: all.isEmpty ? null : () => _export(all, false),
                    child: const Text('TXT'),
                  ),
                  OutlinedButton(
                    onPressed: all.isEmpty ? null : () => _export(all, true),
                    child: const Text('CSV'),
                  ),
                  TextButton.icon(
                    onPressed:
                        all.isEmpty
                            ? null
                            : () => setState(
                              () => hidden.addAll(
                                all.map((item) => item.requestId),
                              ),
                            ),
                    icon: const Icon(Icons.clear_all),
                    label: Text(AppText.of(context, 'clear_view')),
                  ),
                ],
              ),
              Expanded(
                child: ListView.builder(
                  padding: const EdgeInsets.all(12),
                  itemCount: filtered.length,
                  itemBuilder: (_, index) {
                    final item = filtered[index];
                    return Card(
                      child: ListTile(
                        title: Text(item.transcript),
                        subtitle: Text(item.translation),
                        trailing: Text(DateFormat.Hm().format(item.timestamp)),
                      ),
                    );
                  },
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}
