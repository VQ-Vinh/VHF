import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/localization.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../../models/station.dart';
import '../../providers.dart';

class StationListScreen extends ConsumerWidget {
  const StationListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final stations = ref.watch(stationsProvider);
    final now = ref.watch(stationClockProvider).value ?? DateTime.now();
    return Scaffold(
      appBar: PranaPageHeader(
        title: AppText.of(context, 'stations'),
        subtitle: 'PRANA ELEX CONTROL',
        actions: [
          IconButton(
            tooltip: AppText.of(context, 'account'),
            onPressed: () => context.push('/account'),
            icon: const Icon(Icons.person_outline),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.push('/pair'),
        icon: const Icon(Icons.qr_code_scanner),
        label: Text(AppText.of(context, 'pair_station')),
      ),
      body: stations.when(
        loading: () => const _StationSkeleton(),
        error:
            (error, _) => EmptyState(
              icon: Icons.cloud_off,
              title: AppText.of(context, 'load_station_error'),
              subtitle: '$error',
            ),
        data:
            (items) =>
                items.isEmpty
                    ? EmptyState(
                      icon: Icons.add_link,
                      title: AppText.of(context, 'no_station'),
                      subtitle: AppText.of(context, 'no_station_body'),
                    )
                    : LayoutBuilder(
                      builder: (context, constraints) {
                        final columns = constraints.maxWidth >= 720 ? 2 : 1;
                        return GridView.builder(
                          padding: const EdgeInsets.fromLTRB(16, 18, 16, 104),
                          gridDelegate:
                              SliverGridDelegateWithFixedCrossAxisCount(
                                crossAxisCount: columns,
                                childAspectRatio: columns == 1 ? 2.7 : 2,
                                crossAxisSpacing: 14,
                                mainAxisSpacing: 14,
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
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: 42,
                    height: 42,
                    decoration: BoxDecoration(
                      color: PranaTheme.brandBlueSoft,
                      borderRadius: BorderRadius.circular(11),
                    ),
                    child: const Icon(Icons.radio, color: PranaTheme.brandBlue),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          station.name,
                          style: Theme.of(context).textTheme.titleLarge
                              ?.copyWith(fontWeight: FontWeight.w700),
                        ),
                        const SizedBox(height: 3),
                        Text(
                          station.platform,
                          style: const TextStyle(color: Color(0xFF607983)),
                        ),
                      ],
                    ),
                  ),
                  StatusPill(
                    label: online ? 'Online' : 'Offline',
                    online: online,
                  ),
                ],
              ),
              const Spacer(),
              Row(
                children: [
                  Icon(
                    online ? Icons.graphic_eq : Icons.cloud_off,
                    size: 18,
                    color:
                        online ? PranaTheme.brandBlue : const Color(0xFF607983),
                  ),
                  const SizedBox(width: 7),
                  Text(
                    online ? station.captureState.toUpperCase() : 'OFFLINE',
                    style: const TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w800,
                      color: Color(0xFF355762),
                    ),
                  ),
                  const Spacer(),
                  Text(
                    'RX ${station.sequence}',
                    style: const TextStyle(color: Color(0xFF607983)),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StationSkeleton extends StatelessWidget {
  const _StationSkeleton();
  @override
  Widget build(BuildContext context) => ListView.builder(
    padding: const EdgeInsets.all(16),
    itemCount: 3,
    itemBuilder: (_, _) => const Card(child: SizedBox(height: 118)),
  );
}
