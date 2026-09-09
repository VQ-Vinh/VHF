import 'package:prana_mobile/l10n/app_localizations.dart';
import 'package:prana_mobile/core/responsive.dart';
import 'package:prana_mobile/app/di/station_providers.dart';
import 'package:prana_mobile/app/di/auth_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:prana_mobile/core/widgets.dart';
import 'package:prana_mobile/domain/station/station.dart';

class StationListScreen extends ConsumerWidget {
  const StationListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final stations = ref.watch(stationsProvider);
    final now = ref.watch(stationClockProvider).value ?? DateTime.now();
    return ResponsiveScaffold(
      appBar: PranaPageHeader(
        title: AppLocalizations.of(context).stations,
        subtitle: 'PRANA ELEX CONTROL',
        actions: [
          IconButton(
            tooltip: AppLocalizations.of(context).account,
            onPressed: () => context.push('/account'),
            icon: const Icon(Icons.person_outline),
          ),
        ],
      ),
      bottomNavigationBar: Padding(
        padding: const EdgeInsets.all(16),
        child: FilledButton.icon(
          onPressed: () => context.push('/pair'),
          icon: const Icon(Icons.qr_code_scanner),
          label: Text(AppLocalizations.of(context).pairStation),
        ),
      ),
      body: stations.when(
        loading: () => const _StationSkeleton(),
        error:
            (error, _) => EmptyState(
              icon: Icons.cloud_off,
              title: AppLocalizations.of(context).loadStationError,
              subtitle: '$error',
            ),
        data:
            (items) =>
                items.isEmpty
                    ? EmptyState(
                      icon: Icons.add_link,
                      title: AppLocalizations.of(context).noStation,
                      subtitle: AppLocalizations.of(context).noStationBody,
                    )
                    : LayoutBuilder(
                      builder: (context, constraints) {
                        return ListView.builder(
                          padding: const EdgeInsets.fromLTRB(16, 18, 16, 24),
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
                                      '/stations/${items[index].id}/dashboard',
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
      margin: const EdgeInsets.only(bottom: 14),
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
                      color: Theme.of(context).colorScheme.primaryContainer,
                      borderRadius: BorderRadius.circular(11),
                    ),
                    child: Icon(
                      Icons.radio,
                      color: Theme.of(context).colorScheme.onPrimaryContainer,
                    ),
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
                          style: TextStyle(
                            color:
                                Theme.of(context).colorScheme.onSurfaceVariant,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              StatusPill(label: online ? 'Online' : 'Offline', online: online),
              const SizedBox(height: 12),
              Row(
                children: [
                  Icon(
                    online ? Icons.graphic_eq : Icons.cloud_off,
                    size: 18,
                    color:
                        online
                            ? Theme.of(context).colorScheme.primary
                            : Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                  const SizedBox(width: 7),
                  Text(
                    online ? station.captureState.toUpperCase() : 'OFFLINE',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w800,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
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
