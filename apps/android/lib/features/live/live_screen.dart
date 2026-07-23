import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../models/station.dart';
import '../../providers.dart';

class LiveScreen extends ConsumerWidget {
  const LiveScreen({super.key, required this.stationId, this.sessionId});
  final String stationId;
  final String? sessionId;
  static const languages = {
    'vi': 'Tiếng Việt',
    'en': 'English',
    'zh': '中文',
    'ja': '日本語',
    'ko': '한국어',
  };

  Future<void> command(
    BuildContext context,
    WidgetRef ref, {
    bool? running,
    String? language,
    bool retry = false,
  }) async {
    try {
      await ref
          .read(apiProvider)
          .setDesiredState(
            stationId,
            running: running,
            targetLanguage: language,
            retry: retry,
          );
    } catch (error) {
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Không gửi được lệnh: $error')));
      }
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final stationValue = ref.watch(stationProvider(stationId));
    final now = ref.watch(stationClockProvider).value ?? DateTime.now();
    return stationValue.when(
      loading:
          () =>
              const Scaffold(body: Center(child: CircularProgressIndicator())),
      error:
          (error, _) =>
              Scaffold(appBar: AppBar(), body: Center(child: Text('$error'))),
      data: (station) {
        if (station == null) {
          return Scaffold(
            appBar: AppBar(),
            body: const Center(child: Text('Trạm không còn tồn tại.')),
          );
        }
        final selectedSession = sessionId ?? station.sessionId;
        final results = ref.watch(
          liveResultsProvider((
            stationId: stationId,
            sessionId: selectedSession,
          )),
        );
        final online = station.isOnlineAt(now);
        final controlsEnabled = online && !station.commandPending;
        return Scaffold(
          appBar: AppBar(
            title: Text(
              sessionId == null ? station.name : 'Phiên $selectedSession',
            ),
            actions: [
              IconButton(
                tooltip: 'Lịch sử',
                onPressed: () => context.push('/stations/$stationId/history'),
                icon: const Icon(Icons.history),
              ),
            ],
          ),
          body: Column(
            children: [
              _StatusBar(station: station, online: online),
              if (sessionId != null)
                const Padding(
                  padding: EdgeInsets.fromLTRB(16, 10, 16, 0),
                  child: Text(
                    'Đang xem lịch sử. Điều khiển vẫn áp dụng cho trạm hiện tại.',
                  ),
                ),
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
                child: Row(
                  children: [
                    Expanded(
                      child: DropdownButtonFormField<String>(
                        initialValue: station.desired.targetLanguage,
                        decoration: const InputDecoration(
                          labelText: 'Ngôn ngữ dịch',
                        ),
                        items:
                            languages.entries
                                .map(
                                  (entry) => DropdownMenuItem(
                                    value: entry.key,
                                    child: Text(entry.value),
                                  ),
                                )
                                .toList(),
                        onChanged:
                            online
                                ? (value) {
                                  if (value != null) {
                                    command(context, ref, language: value);
                                  }
                                }
                                : null,
                      ),
                    ),
                    const SizedBox(width: 10),
                    IconButton.filledTonal(
                      tooltip: 'Thử lại kết quả gần nhất',
                      onPressed:
                          controlsEnabled
                              ? () => command(context, ref, retry: true)
                              : null,
                      icon: const Icon(Icons.refresh),
                    ),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    onPressed:
                        controlsEnabled
                            ? () => command(
                              context,
                              ref,
                              running: !station.desired.running,
                            )
                            : null,
                    icon: Icon(
                      station.desired.running ? Icons.stop : Icons.play_arrow,
                    ),
                    label: Text(
                      station.commandPending
                          ? 'Đang chờ trạm xác nhận'
                          : station.desired.running
                          ? 'Dừng thu'
                          : 'Bắt đầu thu',
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 8),
              Expanded(
                child: results.when(
                  loading: () => const _ResultSkeleton(),
                  error:
                      (error, _) =>
                          Center(child: Text('Mất kết nối realtime: $error')),
                  data:
                      (items) =>
                          items.isEmpty
                              ? const Center(
                                child: Text(
                                  'Kết quả mới sẽ xuất hiện tại đây.',
                                ),
                              )
                              : ListView.separated(
                                reverse: true,
                                padding: const EdgeInsets.fromLTRB(
                                  16,
                                  8,
                                  16,
                                  24,
                                ),
                                itemCount: items.length,
                                separatorBuilder:
                                    (_, _) => const SizedBox(height: 10),
                                itemBuilder:
                                    (_, index) =>
                                        _ResultCard(result: items[index]),
                              ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _StatusBar extends StatelessWidget {
  const _StatusBar({required this.station, required this.online});
  final StationModel station;
  final bool online;
  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    color: Theme.of(context).colorScheme.surfaceContainer,
    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
    child: Row(
      children: [
        Icon(
          online ? Icons.sensors : Icons.sensors_off,
          color:
              online
                  ? Theme.of(context).colorScheme.primary
                  : Theme.of(context).colorScheme.error,
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            online
                ? '${station.captureState}  |  RX ${station.sequence}'
                : 'Offline quá 15 giây',
          ),
        ),
        if (station.commandPending)
          const SizedBox(
            width: 18,
            height: 18,
            child: CircularProgressIndicator(strokeWidth: 2),
          ),
      ],
    ),
  );
}

class _ResultCard extends StatelessWidget {
  const _ResultCard({required this.result});
  final TranslationResult result;
  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                '#${result.sequence}',
                style: Theme.of(context).textTheme.labelLarge,
              ),
              const Spacer(),
              Text(
                '${result.language.toUpperCase()}  ${(result.confidence * 100).round()}%  ${DateFormat.Hms().format(result.timestamp)}',
              ),
            ],
          ),
          if (result.error != null) ...[
            const SizedBox(height: 10),
            Text(
              result.error!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ],
          if (result.transcript.isNotEmpty) ...[
            const SizedBox(height: 12),
            Text(result.transcript),
          ],
          if (result.translation.isNotEmpty) ...[
            const SizedBox(height: 10),
            Text(
              result.translation,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                color: Theme.of(context).colorScheme.primary,
              ),
            ),
          ],
        ],
      ),
    ),
  );
}

class _ResultSkeleton extends StatelessWidget {
  const _ResultSkeleton();
  @override
  Widget build(BuildContext context) => ListView.builder(
    padding: const EdgeInsets.all(16),
    itemCount: 4,
    itemBuilder: (_, _) => const Card(child: SizedBox(height: 116)),
  );
}
