import 'package:prana_mobile/core/service_messages.dart';
import 'package:prana_mobile/l10n/app_localizations.dart';
import 'package:prana_mobile/core/responsive.dart';
import 'station_settings_controller.dart';
import 'package:prana_mobile/app/di/station_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:prana_mobile/core/theme.dart';
import 'package:prana_mobile/core/widgets.dart';
import 'package:prana_mobile/domain/station/station.dart';

class StationSettingsScreen extends ConsumerStatefulWidget {
  const StationSettingsScreen({
    super.key,
    required this.stationId,
    this.embedded = false,
  });
  final bool embedded;

  final String stationId;

  @override
  ConsumerState<StationSettingsScreen> createState() =>
      _StationSettingsScreenState();
}

class _StationSettingsScreenState extends ConsumerState<StationSettingsScreen> {
  String? mode;
  String? deviceId;
  String? txDeviceId;
  late final StationSettingsController controller;
  @override
  void initState() {
    super.initState();
    controller = StationSettingsController(
      ref.read(stationRepositoryProvider),
      widget.stationId,
      () => ref.read(stationProvider(widget.stationId)).value,
    );
    controller.addListener(_changed);
  }

  void _changed() {
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    controller.removeListener(_changed);
    controller.dispose();
    super.dispose();
  }

  Future<void> _save({
    required StationModel station,
    required String selectedMode,
    required String selectedDevice,
    required bool modeChanged,
    required bool deviceChanged,
    required String selectedTxDevice,
    required bool txDeviceChanged,
  }) async {
    final saved = await controller.save(
      captureMode: modeChanged ? selectedMode : null,
      audioDeviceId: deviceChanged ? selectedDevice : null,
      txAudioDeviceId: txDeviceChanged ? selectedTxDevice : null,
    );
    if (mounted && saved) {
      setState(() {
        mode = null;
        deviceId = null;
        txDeviceId = null;
      });
    }
  }

  Future<void> _refresh(StationModel station) async {
    final refreshed = await controller.refresh(station);
    if (!mounted || refreshed == null) return;
    final selectedMode = mode ?? refreshed.desired.captureMode;
    if (deviceId != null &&
        !(refreshed.capabilities?.audioDevices.any(
              (device) => device.mode == selectedMode && device.id == deviceId,
            ) ??
            false)) {
      setState(() => deviceId = null);
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
            body: Center(
              child: Text(AppLocalizations.of(context).stationMissing),
            ),
          );
        }
        return _stationScaffold(station, now);
      },
    );
  }

  ResponsiveScaffold _baseScaffold({
    required Widget body,
    Widget? bottomNavigationBar,
  }) => ResponsiveScaffold(
    maxWidth: ContentWidth.form,
    appBar:
        widget.embedded
            ? null
            : PranaPageHeader(
              title: AppLocalizations.of(context).stationSettings,
              subtitle: 'REMOTE STATION',
            ),
    body: body,
    bottomNavigationBar: bottomNavigationBar,
  );

  ResponsiveScaffold _stationScaffold(StationModel station, DateTime now) {
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
    final outputDevices =
        capabilities?.audioDevices
            .where((item) => item.mode == 'device' && item.outputChannels > 0)
            .toList() ??
        const <StationAudioDevice>[];
    var selectedTxDevice = txDeviceId ?? station.desired.txAudioDeviceId;
    if (!outputDevices.any((item) => item.id == selectedTxDevice)) {
      // VHF is half-duplex on one sound card, so transmit through the card we
      // record on whenever it can play; otherwise take the only one that can.
      selectedTxDevice =
          outputDevices.any((item) => item.id == selectedDevice)
              ? selectedDevice
              : outputDevices.isEmpty
              ? ''
              : outputDevices.first.id;
    }
    // Nothing to ask while a single card can transmit. Add a second one and
    // rescan, and the picker appears on its own.
    final txChoiceNeeded = outputDevices.length > 1;
    final txDeviceChanged = selectedTxDevice != station.desired.txAudioDeviceId;
    final hasChanges =
        (devices.isNotEmpty || outputDevices.isNotEmpty) &&
        (modeChanged || deviceChanged || txDeviceChanged);
    final operationPending =
        controller.saving || controller.applying || station.commandPending;
    final controlsEnabled =
        online &&
        capabilities != null &&
        !operationPending &&
        !controller.refreshing;
    final canSave = controlsEnabled && hasChanges;

    return _baseScaffold(
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
        children: [
          if (!online) _Notice(AppLocalizations.of(context).offline),
          if (capabilities == null)
            _Notice(AppLocalizations.of(context).capabilitiesUnavailable),
          Text(
            AppLocalizations.of(context).moduleDevices,
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 12),
          _SettingsCard(
            title: 'VHF Device',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  AppLocalizations.of(context).captureMode,
                  style: Theme.of(context).textTheme.labelLarge,
                ),
                const SizedBox(height: 10),
                SizedBox(
                  width: double.infinity,
                  child: SegmentedButton<String>(
                    direction:
                        MediaQuery.textScalerOf(context).scale(320) >
                                MediaQuery.sizeOf(context).width
                            ? Axis.vertical
                            : Axis.horizontal,
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
                              controller.error = null;
                              controller.refreshResultKey = null;
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
                  itemHeight: null,
                  decoration: InputDecoration(
                    labelText: AppLocalizations.of(context).audioDevice,
                  ),
                  items:
                      devices
                          .map(
                            (item) => DropdownMenuItem(
                              value: item.id,
                              child: Text(item.name),
                            ),
                          )
                          .toList(),
                  onChanged:
                      controlsEnabled
                          ? (value) => setState(() {
                            deviceId = value;
                            controller.error = null;
                            controller.refreshResultKey = null;
                          })
                          : null,
                ),
                if (selectedDevice.isNotEmpty)
                  _DeviceDetails(
                    device: devices.firstWhere(
                      (item) => item.id == selectedDevice,
                    ),
                  ),
                if (txChoiceNeeded) ...[
                  const SizedBox(height: 18),
                  // RX and TX share one sound card, so they belong in one card.
                  DropdownButtonFormField<String>(
                    key: const ValueKey('tx-output-device'),
                    initialValue:
                        selectedTxDevice.isEmpty ? null : selectedTxDevice,
                    isExpanded: true,
                    itemHeight: null,
                    decoration: InputDecoration(
                      labelText: AppLocalizations.of(context).txOutputDevice,
                    ),
                    items:
                        outputDevices
                            .map(
                              (device) => DropdownMenuItem(
                                value: device.id,
                                child: Text(device.name),
                              ),
                            )
                            .toList(),
                    onChanged:
                        controlsEnabled
                            ? (value) => setState(() => txDeviceId = value)
                            : null,
                  ),
                ] else if (selectedTxDevice.isNotEmpty)
                  // Silent auto-pick would hide where transmissions go.
                  _TxRoute(
                    key: const ValueKey('tx-output-route'),
                    name:
                        outputDevices
                            .firstWhere((item) => item.id == selectedTxDevice)
                            .name,
                  ),
                const SizedBox(height: 14),
                // Last: the rescan refreshes the lists behind both dropdowns.
                OutlinedButton.icon(
                  onPressed:
                      online && !operationPending && !controller.refreshing
                          ? () => _refresh(station)
                          : null,
                  icon:
                      controller.refreshing
                          ? const SizedBox.square(
                            dimension: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                          : const Icon(Icons.refresh),
                  label: Text(AppLocalizations.of(context).refreshDevices),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          for (final module in [
            ('Speed Device', Icons.speed),
            ('Device 3', Icons.usb),
            ('Device 4', Icons.usb),
          ]) ...[
            _SettingsCard(
              title: module.$1,
              child: Row(
                children: [
                  Icon(module.$2),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(AppLocalizations.of(context).modulePending),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),
          ],
          _SettingsCard(
            title: AppLocalizations.of(context).stationInformation,
            child: Column(
              children: [
                _InformationRow(
                  icon: Icons.graphic_eq,
                  title: AppLocalizations.of(context).activeCapture,
                  value:
                      '${station.activeCaptureMode.toUpperCase()} • '
                      '${_deviceName(capabilities, station.activeAudioDeviceId)}',
                ),
                const Divider(height: 24),
                _InformationRow(
                  icon: Icons.schedule,
                  title: AppLocalizations.of(context).lastDeviceScan,
                  value: capabilities?.updatedAt?.toLocal().toString() ?? '—',
                ),
                const Divider(height: 24),
                _InformationRow(
                  icon: Icons.folder_outlined,
                  title: AppLocalizations.of(context).storagePath,
                  value:
                      capabilities?.storagePath.isNotEmpty == true
                          ? capabilities!.storagePath
                          : '—',
                ),
              ],
            ),
          ),
          if (controller.error != null)
            _InlineMessage(
              text: localizedServiceMessage(context, controller.error!),
              color: Theme.of(context).colorScheme.error,
              icon: Icons.error_outline,
            ),
          if (controller.refreshResultKey != null)
            _InlineMessage(
              text: localizedServiceMessage(
                context,
                controller.refreshResultKey!,
              ),
              color: PranaTheme.brandBlue,
              icon: Icons.info_outline,
            ),
        ],
      ),
      bottomNavigationBar: _SaveBar(
        saving: controller.saving,
        applying: controller.applying || station.commandPending,
        onPressed:
            canSave
                ? () => _save(
                  station: station,
                  selectedMode: selectedMode,
                  selectedDevice: selectedDevice,
                  modeChanged: modeChanged,
                  deviceChanged: deviceChanged,
                  selectedTxDevice: selectedTxDevice,
                  txDeviceChanged: txDeviceChanged,
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
              color: Theme.of(context).colorScheme.onSurface,
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
  });

  final IconData icon;
  final String title;
  final String value;

  @override
  Widget build(BuildContext context) => Row(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Container(
        width: 38,
        height: 38,
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.primaryContainer,
          borderRadius: BorderRadius.all(Radius.circular(10)),
        ),
        child: Icon(
          icon,
          size: 21,
          color: Theme.of(context).colorScheme.onPrimaryContainer,
        ),
      ),
      const SizedBox(width: 12),
      Expanded(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                color: Theme.of(context).colorScheme.onPrimaryContainer,
              ),
            ),
            const SizedBox(height: 3),
            Text(
              value,

              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
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

/// Where transmissions leave the Station when there is only one way out.
class _TxRoute extends StatelessWidget {
  const _TxRoute({super.key, required this.name});

  final String name;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: 14),
    child: Row(
      children: [
        const Icon(
          Icons.volume_up_outlined,
          size: 17,
          color: PranaTheme.brandBlue,
        ),
        const SizedBox(width: 7),
        Expanded(
          child: Text(
            '${AppLocalizations.of(context).txOutputVia}: $name',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
        ),
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
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
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
            ? AppLocalizations.of(context).savingChanges
            : applying
            ? AppLocalizations.of(context).applyingChanges
            : AppLocalizations.of(context).save;
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
          label: Text(label),
        ),
      ),
    );
  }
}
