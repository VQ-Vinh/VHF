import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/localization.dart';
import '../../core/widgets.dart';
import '../../models/station.dart';
import '../../providers.dart';
import '../live/translation_result_card.dart';

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

  int get timezoneOffsetMinutes => DateTime.now().timeZoneOffset.inMinutes;

  @override
  void initState() {
    super.initState();
    days = _loadDays();
  }

  Future<List<StationHistoryDay>> _loadDays() => ref
      .read(apiProvider)
      .stationHistoryDays(
        widget.stationId,
        timezoneOffsetMinutes: timezoneOffsetMinutes,
      );

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
      return _DayHistory(
        stationId: widget.stationId,
        day: selectedDay!,
        timezoneOffsetMinutes: timezoneOffsetMinutes,
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
      body: FutureBuilder<List<StationHistoryDay>>(
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
              title: AppText.of(context, 'no_history_days'),
              subtitle: AppText.of(context, 'no_history_days_body'),
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
                      day.locked
                          ? Icons.lock_clock_outlined
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
    );
  }
}

class _DayHistory extends ConsumerStatefulWidget {
  const _DayHistory({
    required this.stationId,
    required this.day,
    required this.timezoneOffsetMinutes,
    required this.onBack,
  });

  final String stationId;
  final StationHistoryDay day;
  final int timezoneOffsetMinutes;
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
