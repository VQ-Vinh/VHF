import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:just_audio/just_audio.dart';
import 'package:path_provider/path_provider.dart';

import '../../core/localization.dart';
import '../../core/widgets.dart';
import '../../models/station.dart';
import '../../providers.dart';
import '../live/translation_result_card.dart';
import '../tx/domain/tx_draft.dart';

enum _HistoryMode { rx, tx }

class HistoryScreen extends ConsumerStatefulWidget {
  const HistoryScreen({
    super.key,
    required this.stationId,
    this.embedded = false,
  });

  final String stationId;
  final bool embedded;

  @override
  ConsumerState<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends ConsumerState<HistoryScreen> {
  StationHistoryDay? selectedDay;
  late Future<List<StationHistoryDay>> days;
  _HistoryMode mode = _HistoryMode.rx;

  int get timezoneOffsetMinutes => DateTime.now().timeZoneOffset.inMinutes;

  // The chosen country's zone, so days group the same way they are stored.
  String? get timezoneName => ref.read(userRegionProvider).timezoneName;

  @override
  void initState() {
    super.initState();
    days = _loadDays();
  }

  Future<List<StationHistoryDay>> _loadDays() {
    final api = ref.read(apiProvider);
    return mode == _HistoryMode.rx
        ? api.stationHistoryDays(
          widget.stationId,
          timezoneOffsetMinutes: timezoneOffsetMinutes,
          timezone: timezoneName,
        )
        : api.txHistoryDays(
          widget.stationId,
          timezoneOffsetMinutes: timezoneOffsetMinutes,
          timezone: timezoneName,
        );
  }

  void _selectMode(_HistoryMode value) {
    if (value == mode) return;
    setState(() {
      mode = value;
      selectedDay = null;
      days = _loadDays();
    });
  }

  Future<void> _refresh() async {
    final refreshed = _loadDays();
    setState(() => days = refreshed);
    await refreshed;
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(authStateProvider).value;
    if (user == null) return const SizedBox.shrink();
    if (selectedDay != null) {
      return mode == _HistoryMode.rx
          ? _DayHistory(
            stationId: widget.stationId,
            day: selectedDay!,
            timezoneOffsetMinutes: timezoneOffsetMinutes,
            timezoneName: timezoneName,
            onBack: () => setState(() => selectedDay = null),
          )
          : _TxDayHistory(
            stationId: widget.stationId,
            day: selectedDay!,
            timezoneOffsetMinutes: timezoneOffsetMinutes,
            timezoneName: timezoneName,
            onBack: () => setState(() => selectedDay = null),
          );
    }
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
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 4),
            child: SizedBox(
              width: double.infinity,
              child: SegmentedButton<_HistoryMode>(
                segments: const [
                  ButtonSegment(value: _HistoryMode.rx, label: Text('RX')),
                  ButtonSegment(value: _HistoryMode.tx, label: Text('TX')),
                ],
                selected: {mode},
                onSelectionChanged: (value) => _selectMode(value.first),
              ),
            ),
          ),
          Expanded(
            child: FutureBuilder<List<StationHistoryDay>>(
              future: days,
              builder: (context, snapshot) {
                if (snapshot.hasError) {
                  return Center(child: Text('${snapshot.error}'));
                }
                if (!snapshot.hasData) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (snapshot.data!.isEmpty) {
                  return EmptyState(
                    icon: Icons.history,
                    title: AppText.of(
                      context,
                      mode == _HistoryMode.rx
                          ? 'no_history_days'
                          : 'tx_history_empty',
                    ),
                    subtitle: AppText.of(
                      context,
                      mode == _HistoryMode.rx
                          ? 'no_history_days_body'
                          : 'tx_history_empty_body',
                    ),
                  );
                }
                return RefreshIndicator(
                  onRefresh: _refresh,
                  child: ListView.separated(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.all(16),
                    itemCount: snapshot.data!.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 10),
                    itemBuilder: (_, index) {
                      final day = snapshot.data![index];
                      final date = DateFormat('dd/MM/yyyy').format(day.date);
                      final timeRange =
                          '${DateFormat.Hm().format(day.firstResultAt.toLocal())}'
                          '–${DateFormat.Hm().format(day.lastResultAt.toLocal())}';
                      return Card(
                        child: ListTile(
                          leading: const Icon(Icons.calendar_today_outlined),
                          title: Text(
                            AppText.format(context, 'history_day_title', {
                              'date': date,
                            }),
                          ),
                          subtitle: Text(
                            AppText.format(context, 'history_day_summary', {
                              'count': day.resultCount,
                              'range': timeRange,
                            }),
                          ),
                          trailing: Icon(
                            // A locked day is past the plan window, so it will
                            // never unlock on its own.
                            day.locked
                                ? Icons.lock_outline
                                : Icons.chevron_right,
                          ),
                          onTap:
                              day.locked
                                  ? null
                                  : () => setState(() => selectedDay = day),
                        ),
                      );
                    },
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _TxDayHistory extends ConsumerStatefulWidget {
  const _TxDayHistory({
    required this.stationId,
    required this.day,
    required this.timezoneOffsetMinutes,
    required this.timezoneName,
    required this.onBack,
  });

  final String stationId;
  final StationHistoryDay day;
  final int timezoneOffsetMinutes;
  final String? timezoneName;
  final VoidCallback onBack;

  @override
  ConsumerState<_TxDayHistory> createState() => _TxDayHistoryState();
}

class _TxDayHistoryState extends ConsumerState<_TxDayHistory> {
  final search = TextEditingController();
  final player = AudioPlayer();
  late Future<List<TxDraft>> jobs;
  String query = '';
  String? playingId;

  @override
  void initState() {
    super.initState();
    jobs = ref
        .read(apiProvider)
        .txHistoryDayJobs(
          widget.stationId,
          widget.day.apiDate,
          timezoneOffsetMinutes: widget.timezoneOffsetMinutes,
          timezone: widget.timezoneName,
        );
    player.playerStateStream.listen((state) {
      if (state.processingState == ProcessingState.completed && mounted) {
        setState(() => playingId = null);
      }
    });
  }

  @override
  void dispose() {
    search.dispose();
    player.dispose();
    super.dispose();
  }

  Future<void> _play(TxDraft job) async {
    if (!job.outputAvailable) return;
    if (playingId == job.id) {
      await player.stop();
      if (mounted) setState(() => playingId = null);
      return;
    }
    setState(() => playingId = job.id);
    try {
      final bytes = await ref
          .read(apiProvider)
          .txHistoryAudio(widget.stationId, job.id);
      final directory = await getTemporaryDirectory();
      final file = File('${directory.path}/prana-tx-history-${job.id}.wav');
      await file.writeAsBytes(bytes, flush: true);
      await player.setFilePath(file.path);
      await player.play();
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(error.toString())));
      }
    } finally {
      if (mounted && player.processingState != ProcessingState.ready) {
        setState(() => playingId = null);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final date = DateFormat('dd/MM/yyyy').format(widget.day.date);
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          onPressed: widget.onBack,
          icon: const Icon(Icons.arrow_back),
        ),
        title: Text(
          AppText.format(context, 'history_day_title', {'date': date}),
        ),
      ),
      body: FutureBuilder<List<TxDraft>>(
        future: jobs,
        builder: (context, snapshot) {
          if (snapshot.hasError) {
            return Center(child: Text('${snapshot.error}'));
          }
          if (!snapshot.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          final filtered =
              snapshot.data!.where((job) {
                final content =
                    '${job.transcript} ${job.translation}'.toLowerCase();
                return content.contains(query.toLowerCase());
              }).toList();
          return Column(
            children: [
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
              Expanded(
                child:
                    filtered.isEmpty
                        ? EmptyState(
                          icon: Icons.send_outlined,
                          title: AppText.of(context, 'tx_history_empty'),
                          subtitle: AppText.of(
                            context,
                            'tx_history_empty_body',
                          ),
                        )
                        : ListView.separated(
                          padding: const EdgeInsets.fromLTRB(16, 6, 16, 18),
                          itemCount: filtered.length,
                          separatorBuilder:
                              (_, _) => const SizedBox(height: 10),
                          itemBuilder:
                              (_, index) => _TxHistoryCard(
                                job: filtered[index],
                                playing: playingId == filtered[index].id,
                                onPlay: () => _play(filtered[index]),
                              ),
                        ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _TxHistoryCard extends StatelessWidget {
  const _TxHistoryCard({
    required this.job,
    required this.playing,
    required this.onPlay,
  });

  final TxDraft job;
  final bool playing;
  final VoidCallback onPlay;

  @override
  Widget build(BuildContext context) {
    final time =
        job.createdAt == null
            ? '--:--:--'
            : DateFormat.Hms().format(job.createdAt!.toLocal());
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    '$time  ·  ${job.detectedLanguage.toUpperCase()} → '
                    '${job.targetLanguage.toUpperCase()}  ·  '
                    '${AppText.of(context, 'tx_status_${job.status}')}',
                    style: Theme.of(context).textTheme.labelMedium,
                  ),
                ),
                IconButton(
                  tooltip: AppText.of(context, 'play_audio'),
                  onPressed: job.outputAvailable ? onPlay : null,
                  icon: Icon(
                    playing
                        ? Icons.stop_circle_outlined
                        : Icons.volume_up_outlined,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(job.transcript),
            const SizedBox(height: 10),
            Text(
              job.translation,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 4,
              children: [
                if (job.translationEdited)
                  Chip(label: Text(AppText.of(context, 'tx_history_edited'))),
                Chip(
                  label: Text(
                    AppText.format(context, 'tx_history_attempt', {
                      'attempt': job.attempt,
                    }),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _DayHistory extends ConsumerStatefulWidget {
  const _DayHistory({
    required this.stationId,
    required this.day,
    required this.timezoneOffsetMinutes,
    required this.timezoneName,
    required this.onBack,
  });

  final String stationId;
  final StationHistoryDay day;
  final int timezoneOffsetMinutes;
  final String? timezoneName;
  final VoidCallback onBack;

  @override
  ConsumerState<_DayHistory> createState() => _DayHistoryState();
}

class _DayHistoryState extends ConsumerState<_DayHistory> {
  final search = TextEditingController();
  late Future<List<TranslationResult>> results;
  String query = '';

  @override
  void initState() {
    super.initState();
    results = ref
        .read(apiProvider)
        .stationHistoryDayResults(
          widget.stationId,
          widget.day.apiDate,
          timezoneOffsetMinutes: widget.timezoneOffsetMinutes,
          timezone: widget.timezoneName,
        );
  }

  @override
  void dispose() {
    search.dispose();
    super.dispose();
  }

  String _title(BuildContext context) => AppText.format(
    context,
    'history_day_title',
    {'date': DateFormat('dd/MM/yyyy').format(widget.day.date)},
  );

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          onPressed: widget.onBack,
          icon: const Icon(Icons.arrow_back),
        ),
        title: Text(_title(context)),
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
          final filtered =
              snapshot.data!.where((item) {
                final text =
                    '${item.transcript} ${item.translation}'.toLowerCase();
                return text.contains(query.toLowerCase());
              }).toList();
          return Column(
            children: [
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
              Expanded(
                child: ListView.separated(
                  padding: const EdgeInsets.fromLTRB(16, 6, 16, 18),
                  itemCount: filtered.length,
                  separatorBuilder: (_, _) => const SizedBox(height: 10),
                  itemBuilder: (_, index) {
                    final item = filtered[index];
                    return TranslationResultCard(
                      key: ValueKey(item.requestId),
                      result: item,
                      showPlayback: false,
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
