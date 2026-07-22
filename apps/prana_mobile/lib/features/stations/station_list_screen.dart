import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../models/station.dart';
import '../../providers.dart';

class StationListScreen extends ConsumerWidget {
  const StationListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final stations = ref.watch(stationsProvider);
    final now = ref.watch(stationClockProvider).value ?? DateTime.now();
    return Scaffold(
      appBar: AppBar(
        title: const Text('Trạm của tôi'),
        actions: [
          IconButton(
            tooltip: 'Tài khoản',
            onPressed: () => context.push('/account'),
            icon: const Icon(Icons.person_outline),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.push('/pair'),
        icon: const Icon(Icons.qr_code_scanner),
        label: const Text('Ghép trạm'),
      ),
      body: stations.when(
        loading: () => const _StationSkeleton(),
        error:
            (error, _) => _Message(
              icon: Icons.cloud_off,
              text: 'Không tải được trạm\n$error',
            ),
        data:
            (items) =>
                items.isEmpty
                    ? const _Message(
                      icon: Icons.add_link,
                      text:
                          'Chưa có trạm. Quét tem QR trên thiết bị hoặc dùng mã tạm thời.',
                    )
                    : LayoutBuilder(
                      builder: (context, constraints) {
                        final columns = constraints.maxWidth >= 700 ? 2 : 1;
                        return GridView.builder(
                          padding: const EdgeInsets.fromLTRB(16, 12, 16, 96),
                          gridDelegate:
                              SliverGridDelegateWithFixedCrossAxisCount(
                                crossAxisCount: columns,
                                childAspectRatio: columns == 1 ? 2.2 : 1.8,
                                crossAxisSpacing: 12,
                                mainAxisSpacing: 12,
                              ),
                          itemCount: items.length,
                          itemBuilder:
                              (_, index) => _StationCard(
                                station: items[index],
                                now: now,
                                onTap: () async {
                                  await ref
                                      .read(secureStorageProvider)
                                      .write(
                                        key: 'last_station_id',
                                        value: items[index].id,
                                      );
                                  if (context.mounted) {
                                    context.push(
                                      '/stations/${items[index].id}/live',
                                    );
                                  }
                                },
                              ),
                        );
                      },
                    ),
      ),
    );
  }
}

class _StationCard extends StatelessWidget {
  const _StationCard({
    required this.station,
    required this.now,
    required this.onTap,
  });
  final StationModel station;
  final DateTime now;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final online = station.isOnlineAt(now);
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      station.name,
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                  ),
                  Icon(
                    online ? Icons.cloud_done : Icons.cloud_off,
                    color:
                        online
                            ? Theme.of(context).colorScheme.primary
                            : Theme.of(context).colorScheme.outline,
                  ),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                station.platform,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              const Spacer(),
              Text(
                online ? station.captureState.toUpperCase() : 'OFFLINE',
                style: Theme.of(context).textTheme.labelLarge,
              ),
              const SizedBox(height: 6),
              Text(
                'Phiên ${station.sessionId.isEmpty ? "chưa bắt đầu" : station.sessionId}  |  RX ${station.sequence}',
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Message extends StatelessWidget {
  const _Message({required this.icon, required this.text});
  final IconData icon;
  final String text;
  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(32),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 48),
          const SizedBox(height: 16),
          Text(text, textAlign: TextAlign.center),
        ],
      ),
    ),
  );
}

class _StationSkeleton extends StatelessWidget {
  const _StationSkeleton();
  @override
  Widget build(BuildContext context) => ListView.builder(
    padding: const EdgeInsets.all(16),
    itemCount: 3,
    itemBuilder: (_, _) => const Card(child: SizedBox(height: 128)),
  );
}
