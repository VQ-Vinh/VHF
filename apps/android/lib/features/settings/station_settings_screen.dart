import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/localization.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../../models/station.dart';
import '../../providers.dart';

class StationSettingsScreen extends ConsumerStatefulWidget {
  const StationSettingsScreen({super.key, required this.stationId});

  final String stationId;

  @override
  ConsumerState<StationSettingsScreen> createState() =>
      _StationSettingsScreenState();
}

class _StationSettingsScreenState extends ConsumerState<StationSettingsScreen> {
  String? mode;
  String? deviceId;
  bool saving = false;
  bool applying = false;
  bool refreshing = false;
  String? error;
  String? refreshResultKey;

  Future<void> _save({
    required StationModel station,
    required String selectedMode,
    required String selectedDevice,
    required bool modeChanged,
    required bool deviceChanged,
  }) async {
    if (!modeChanged && !deviceChanged) return;
    setState(() {
      saving = true;
      error = null;
      refreshResultKey = null;
    });
    try {
      await ref
          .read(apiProvider)
          .setDesiredState(
            station.id,
            captureMode: modeChanged ? selectedMode : null,
            audioDeviceId: deviceChanged ? selectedDevice : null,
          );
      if (!mounted) return;
      setState(() {
        saving = false;
        applying = true;
      });

      final warningDeadline = DateTime.now().add(const Duration(seconds: 12));
      var syncWarningShown = false;
      while (mounted) {
        final current = ref.read(stationProvider(widget.stationId)).value;
        if (current != null &&
            (!modeChanged || current.desired.captureMode == selectedMode) &&
            (!deviceChanged ||
                current.desired.audioDeviceId == selectedDevice)) {
          setState(() {
            mode = null;
            deviceId = null;
            applying = false;
            error = null;
          });
          return;
        }
        if (!syncWarningShown && DateTime.now().isAfter(warningDeadline)) {
          syncWarningShown = true;
          setState(() {
            error = AppText.of(context, 'settings_sync_delayed');
          });
        }
        await Future<void>.delayed(
          syncWarningShown
              ? const Duration(seconds: 1)
              : const Duration(milliseconds: 200),
        );
      }
    } catch (exception) {
      if (mounted) {
        setState(() {
          error = exception.toString();
          saving = false;
          applying = false;
        });
      }
    }
  }

  Future<void> _refresh(StationModel station) async {
    final previousUpdatedAt = station.capabilities?.updatedAt;
    final previousHash = station.capabilities?.capabilityHash ?? '';
    final localMode = mode;
    final localDeviceId = deviceId;
    setState(() {
      refreshing = true;
      error = null;
      refreshResultKey = null;
    });
    try {
      await ref
          .read(apiProvider)
          .setDesiredState(widget.stationId, refreshCapabilities: true);
      final deadline = DateTime.now().add(const Duration(seconds: 12));
      StationModel? refreshed;
      while (mounted && DateTime.now().isBefore(deadline)) {
        await Future<void>.delayed(const Duration(milliseconds: 250));
        refreshed = ref.read(stationProvider(widget.stationId)).value;
        final updatedAt = refreshed?.capabilities?.updatedAt;
        if (updatedAt != null &&
            (previousUpdatedAt == null ||
                updatedAt.isAfter(previousUpdatedAt))) {
          break;
        }
        refreshed = null;
      }
      if (!mounted) return;
      if (refreshed == null) {
        setState(() => refreshResultKey = 'device_scan_timeout');
      } else {
        final changed = refreshed.capabilities?.capabilityHash != previousHash;
        final refreshedMode = localMode ?? refreshed.desired.captureMode;
        final localDeviceStillAvailable =
            localDeviceId == null ||
            refreshed.capabilities?.audioDevices.any(
                  (item) =>
                      item.mode == refreshedMode && item.id == localDeviceId,
                ) ==
                true;
        setState(() {
          // Preserve an unsaved selection if it is still available. Otherwise
          // fall back to the latest desired state and re-evaluate validity.
          if (!localDeviceStillAvailable) deviceId = null;
          refreshResultKey =
              changed ? 'device_scan_changed' : 'device_scan_unchanged';
        });
      }
    } catch (exception) {
      if (mounted) setState(() => error = exception.toString());
    } finally {
      if (mounted) setState(() => refreshing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final value = ref.watch(stationProvider(widget.stationId));
    final now = ref.watch(stationClockProvider).value ?? DateTime.now();
    return value.when(
      loading:
          () => _baseScaffold(
            body: const Center(child: CircularProgressIndicator()),
          ),
      error: (error, _) => _baseScaffold(body: Center(child: Text('$error'))),
      data: (station) {
        if (station == null) {
          return _baseScaffold(
            body: Center(child: Text(AppText.of(context, 'station_missing'))),
          );
        }
        return _stationScaffold(station, now);
      },
    );
  }

  Scaffold _baseScaffold({required Widget body, Widget? bottomNavigationBar}) =>
      Scaffold(
        appBar: PranaPageHeader(
          title: AppText.of(context, 'station_settings'),
          subtitle: 'REMOTE STATION',
        ),
        body: body,
        bottomNavigationBar: bottomNavigationBar,
      );

  Scaffold _stationScaffold(StationModel station, DateTime now) {
    final capabilities = station.capabilities;
    final online = station.isOnlineAt(now);
    final selectedMode = mode ?? station.desired.captureMode;
    final devices =
        capabilities?.audioDevices
            .where((item) => item.mode == selectedMode)
            .toList() ??
        const <StationAudioDevice>[];
    var selectedDevice = deviceId ?? station.desired.audioDeviceId;
    if (!devices.any((item) => item.id == selectedDevice)) {
      selectedDevice = devices.isEmpty ? '' : devices.first.id;
    }

    final modeChanged = selectedMode != station.desired.captureMode;
    final deviceChanged = selectedDevice != station.desired.audioDeviceId;
    final hasChanges = devices.isNotEmpty && (modeChanged || deviceChanged);
    final operationPending = saving || applying || station.commandPending;
    final controlsEnabled =
        online && capabilities != null && !operationPending && !refreshing;
    final canSave = controlsEnabled && hasChanges;

    return _baseScaffold(
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
        children: [
          if (!online) _Notice(AppText.of(context, 'offline')),
          if (capabilities == null)
            _Notice(AppText.of(context, 'capabilities_unavailable')),
          _SettingsCard(
            title: AppText.of(context, 'audio_source'),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  AppText.of(context, 'capture_mode'),
                  style: Theme.of(context).textTheme.labelLarge,
                ),
                const SizedBox(height: 10),
                SizedBox(
                  width: double.infinity,
                  child: SegmentedButton<String>(
                    segments:
                        (capabilities?.captureModes ??
                                const ['device', 'loopback'])
                            .map(
                              (item) => ButtonSegment(
                                value: item,
                                label: Text(item.toUpperCase()),
                              ),
                            )
                            .toList(),
                    selected: {selectedMode},
                    showSelectedIcon: true,
                    onSelectionChanged:
                        controlsEnabled
                            ? (value) => setState(() {
                              mode = value.first;
                              deviceId = null;
                              error = null;
                              refreshResultKey = null;
                            })
                            : null,
                    style: const ButtonStyle(
                      visualDensity: VisualDensity.comfortable,
                    ),
                  ),
                ),
                const SizedBox(height: 18),
                DropdownButtonFormField<String>(
                  key: ValueKey(
                    '$selectedMode|$selectedDevice|'
                    '${capabilities?.capabilityHash ?? ''}',
                  ),
                  initialValue: selectedDevice.isEmpty ? null : selectedDevice,
                  isExpanded: true,
                  decoration: InputDecoration(
                    labelText: AppText.of(context, 'audio_device'),
                  ),
                  items:
                      devices
                          .map(
                            (item) => DropdownMenuItem(
                              value: item.id,
                              child: Text(
                                item.name,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          )
                          .toList(),
                  onChanged:
                      controlsEnabled
                          ? (value) => setState(() {
                            deviceId = value;
                            error = null;
                            refreshResultKey = null;
                          })
                          : null,
                ),
                if (selectedDevice.isNotEmpty)
                  _DeviceDetails(
                    device: devices.firstWhere(
                      (item) => item.id == selectedDevice,
                    ),
                  ),
                const SizedBox(height: 14),
                OutlinedButton.icon(
                  onPressed:
                      online && !operationPending && !refreshing
                          ? () => _refresh(station)
                          : null,
                  icon:
                      refreshing
                          ? const SizedBox.square(
                            dimension: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                          : const Icon(Icons.refresh),
                  label: Text(AppText.of(context, 'refresh_devices')),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          _SettingsCard(
            title: AppText.of(context, 'station_information'),
            child: Column(
              children: [
                _InformationRow(
                  icon: Icons.graphic_eq,
                  title: AppText.of(context, 'active_capture'),
                  value:
                      '${station.activeCaptureMode.toUpperCase()} • '
                      '${_deviceName(capabilities, station.activeAudioDeviceId)}',
                ),
                const Divider(height: 24),
                _InformationRow(
                  icon: Icons.schedule,
                  title: AppText.of(context, 'last_device_scan'),
                  value: capabilities?.updatedAt?.toLocal().toString() ?? '—',
                ),
                const Divider(height: 24),
                _InformationRow(
                  icon: Icons.folder_outlined,
                  title: AppText.of(context, 'storage_path'),
                  value:
                      capabilities?.storagePath.isNotEmpty == true
                          ? capabilities!.storagePath
                          : '—',
                  maxLines: 2,
                ),
              ],
            ),
          ),
          if (error != null)
            _InlineMessage(
              text: error!,
              color: Theme.of(context).colorScheme.error,
              icon: Icons.error_outline,
            ),
          if (refreshResultKey != null)
            _InlineMessage(
              text: AppText.of(context, refreshResultKey!),
              color: PranaTheme.brandBlue,
              icon: Icons.info_outline,
            ),
        ],
      ),
      bottomNavigationBar: _SaveBar(
        saving: saving,
        applying: applying || station.commandPending,
        onPressed:
            canSave
                ? () => _save(
                  station: station,
                  selectedMode: selectedMode,
                  selectedDevice: selectedDevice,
                  modeChanged: modeChanged,
                  deviceChanged: deviceChanged,
                )
                : null,
      ),
    );
  }

  String _deviceName(StationCapabilities? capabilities, String id) {
    if (id.isEmpty) return '—';
    for (final device
        in capabilities?.audioDevices ?? const <StationAudioDevice>[]) {
      if (device.id == id) return device.name;
    }
    return id;
  }
}

class _SettingsCard extends StatelessWidget {
  const _SettingsCard({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            title,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.w700,
              color: PranaTheme.navy,
            ),
          ),
          const SizedBox(height: 16),
          child,
        ],
      ),
    ),
  );
}

class _InformationRow extends StatelessWidget {
  const _InformationRow({
    required this.icon,
    required this.title,
    required this.value,
    this.maxLines = 2,
  });

  final IconData icon;
  final String title;
  final String value;
  final int maxLines;

  @override
  Widget build(BuildContext context) => Row(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Container(
        width: 38,
        height: 38,
        decoration: const BoxDecoration(
          color: PranaTheme.brandBlueSoft,
          borderRadius: BorderRadius.all(Radius.circular(10)),
        ),
        child: Icon(icon, size: 21, color: PranaTheme.brandBlue),
      ),
      const SizedBox(width: 12),
      Expanded(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: Theme.of(
                context,
              ).textTheme.labelLarge?.copyWith(color: PranaTheme.navy),
            ),
            const SizedBox(height: 3),
            Text(
              value,
              maxLines: maxLines,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: PranaTheme.muted,
                height: 1.35,
              ),
            ),
          ],
        ),
      ),
    ],
  );
}

class _Notice extends StatelessWidget {
  const _Notice(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: Material(
      color: const Color(0xFFFFF1D6),
      borderRadius: BorderRadius.circular(12),
      child: Padding(padding: const EdgeInsets.all(12), child: Text(text)),
    ),
  );
}

class _InlineMessage extends StatelessWidget {
  const _InlineMessage({
    required this.text,
    required this.color,
    required this.icon,
  });

  final String text;
  final Color color;
  final IconData icon;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: 14),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 19, color: color),
        const SizedBox(width: 8),
        Expanded(child: Text(text, style: TextStyle(color: color))),
      ],
    ),
  );
}

class _DeviceDetails extends StatelessWidget {
  const _DeviceDetails({required this.device});

  final StationAudioDevice device;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: 10),
    child: Row(
      children: [
        const Icon(Icons.tune, size: 17, color: PranaTheme.brandBlue),
        const SizedBox(width: 7),
        Expanded(
          child: Text(
            '${device.hostApi} • ${device.inputChannels} in / '
            '${device.outputChannels} out • ${device.sampleRate} Hz',
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: PranaTheme.muted),
          ),
        ),
      ],
    ),
  );
}

class _SaveBar extends StatelessWidget {
  const _SaveBar({
    required this.saving,
    required this.applying,
    required this.onPressed,
  });

  final bool saving;
  final bool applying;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    final busy = saving || applying;
    final label =
        saving
            ? AppText.of(context, 'saving_changes')
            : applying
            ? AppText.of(context, 'applying_changes')
            : AppText.of(context, 'save');
    return Material(
      color: Theme.of(context).colorScheme.surface,
      child: SafeArea(
        top: false,
        minimum: const EdgeInsets.fromLTRB(16, 12, 16, 12),
        child: FilledButton.icon(
          onPressed: onPressed,
          icon:
              busy
                  ? const SizedBox.square(
                    dimension: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Colors.white,
                    ),
                  )
                  : const Icon(Icons.save_outlined),
          label: Text(label, maxLines: 1),
        ),
      ),
    );
  }
}
