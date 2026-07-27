import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/localization.dart';
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
  bool? autoStart;
  bool saving = false;
  bool refreshing = false;
  String? error;
  String? refreshResultKey;

  Future<void> _save(StationModel station) async {
    setState(() {
      saving = true;
      error = null;
    });
    try {
      await ref
          .read(apiProvider)
          .setDesiredState(
            station.id,
            captureMode:
                station.isOnline ? mode ?? station.desired.captureMode : null,
            audioDeviceId:
                station.isOnline
                    ? deviceId ?? station.desired.audioDeviceId
                    : null,
            autoStartCapture: autoStart ?? station.desired.autoStartCapture,
          );
    } catch (exception) {
      if (mounted) setState(() => error = exception.toString());
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  Future<void> _refresh(StationModel station) async {
    final previousUpdatedAt = station.capabilities?.updatedAt;
    final previousHash = station.capabilities?.capabilityHash ?? '';
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
        setState(() {
          // Discard a local selection that may refer to a disconnected device.
          deviceId = null;
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
    return Scaffold(
      appBar: PranaPageHeader(
        title: AppText.of(context, 'station_settings'),
        subtitle: 'REMOTE STATION',
      ),
      body: value.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => Center(child: Text('$error')),
        data: (station) {
          if (station == null) {
            return Center(child: Text(AppText.of(context, 'station_missing')));
          }
          final online = station.isOnlineAt(now);
          final capabilities = station.capabilities;
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
          final enabled =
              online && capabilities != null && !saving && !refreshing;
          final autoStartChanged =
              autoStart != null &&
              autoStart != station.desired.autoStartCapture;

          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              if (!online) _Notice(AppText.of(context, 'offline')),
              if (capabilities == null)
                _Notice(AppText.of(context, 'capabilities_unavailable')),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(18),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                        AppText.of(context, 'capture_mode'),
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 12),
                      SegmentedButton<String>(
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
                        onSelectionChanged:
                            enabled
                                ? (value) => setState(() {
                                  mode = value.first;
                                  deviceId = null;
                                })
                                : null,
                      ),
                      const SizedBox(height: 18),
                      DropdownButtonFormField<String>(
                        key: ValueKey(
                          '$selectedMode|$selectedDevice|'
                          '${capabilities?.capabilityHash ?? ''}',
                        ),
                        initialValue:
                            selectedDevice.isEmpty ? null : selectedDevice,
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
                            enabled
                                ? (value) => setState(() => deviceId = value)
                                : null,
                      ),
                      if (selectedDevice.isNotEmpty)
                        _DeviceDetails(
                          device: devices.firstWhere(
                            (item) => item.id == selectedDevice,
                          ),
                        ),
                      const SizedBox(height: 8),
                      OutlinedButton.icon(
                        onPressed:
                            online && !saving && !refreshing
                                ? () => _refresh(station)
                                : null,
                        icon:
                            refreshing
                                ? const SizedBox.square(
                                  dimension: 18,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                  ),
                                )
                                : const Icon(Icons.refresh),
                        label: Text(AppText.of(context, 'refresh_devices')),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Card(
                child: SwitchListTile(
                  value: autoStart ?? station.desired.autoStartCapture,
                  onChanged:
                      !saving
                          ? (value) => setState(() => autoStart = value)
                          : null,
                  title: Text(AppText.of(context, 'auto_start_capture')),
                  subtitle: Text(
                    AppText.of(context, 'auto_start_capture_help'),
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Card(
                child: Column(
                  children: [
                    ListTile(
                      leading: const Icon(Icons.graphic_eq),
                      title: Text(AppText.of(context, 'active_capture')),
                      subtitle: Text(
                        '${station.activeCaptureMode.toUpperCase()} • '
                        '${_deviceName(capabilities, station.activeAudioDeviceId)}',
                      ),
                    ),
                    ListTile(
                      leading: const Icon(Icons.schedule),
                      title: Text(AppText.of(context, 'last_device_scan')),
                      subtitle: Text(
                        capabilities?.updatedAt?.toLocal().toString() ?? '—',
                      ),
                    ),
                    ListTile(
                      leading: const Icon(Icons.folder_outlined),
                      title: Text(AppText.of(context, 'storage_path')),
                      subtitle: Text(
                        capabilities?.storagePath.isNotEmpty == true
                            ? capabilities!.storagePath
                            : '—',
                      ),
                    ),
                  ],
                ),
              ),
              if (station.commandPending)
                Padding(
                  padding: const EdgeInsets.only(top: 12),
                  child: Text(AppText.of(context, 'waiting')),
                ),
              if (error != null)
                Padding(
                  padding: const EdgeInsets.only(top: 12),
                  child: Text(
                    error!,
                    style: const TextStyle(color: Colors.red),
                  ),
                ),
              if (refreshResultKey != null)
                Padding(
                  padding: const EdgeInsets.only(top: 12),
                  child: Text(AppText.of(context, refreshResultKey!)),
                ),
              const SizedBox(height: 20),
              FilledButton.icon(
                onPressed:
                    ((enabled && devices.isNotEmpty) || autoStartChanged) &&
                            !station.commandPending
                        ? () {
                          if (online) deviceId = selectedDevice;
                          _save(station);
                        }
                        : null,
                icon:
                    saving
                        ? const SizedBox.square(
                          dimension: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                        : const Icon(Icons.save_outlined),
                label: Text(AppText.of(context, 'save')),
              ),
            ],
          );
        },
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

class _DeviceDetails extends StatelessWidget {
  const _DeviceDetails({required this.device});
  final StationAudioDevice device;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: 10),
    child: Text(
      '${device.hostApi} • ${device.inputChannels} in / '
      '${device.outputChannels} out • ${device.sampleRate} Hz',
      style: Theme.of(context).textTheme.bodySmall,
    ),
  );
}
