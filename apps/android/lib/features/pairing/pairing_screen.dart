import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../../core/localization.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../../providers.dart';

enum PairingMode { label, temporary }

typedef PairingLink = ({PairingMode mode, String identifier, String code});

class ActivationCodeInputFormatter extends TextInputFormatter {
  static const rawLength = 16;
  String _normalized(String value) =>
      value.replaceAll(RegExp(r'[^A-Za-z0-9]'), '').toUpperCase();
  @override
  TextEditingValue formatEditUpdate(
    TextEditingValue oldValue,
    TextEditingValue newValue,
  ) {
    final raw = _normalized(newValue.text);
    final limited = raw.substring(0, raw.length.clamp(0, rawLength));
    final groups = <String>[];
    for (var start = 0; start < limited.length; start += 4) {
      groups.add(
        limited.substring(start, (start + 4).clamp(0, limited.length)),
      );
    }
    final formatted = groups.join(' ');
    return TextEditingValue(
      text: formatted,
      selection: TextSelection.collapsed(offset: formatted.length),
    );
  }
}

PairingLink? parsePairingLink(Uri uri) {
  if (uri.scheme != 'prana-elex') return null;
  if (uri.path == '/activate' || uri.host == 'activate') {
    return (
      mode: PairingMode.label,
      identifier: uri.queryParameters['id'] ?? '',
      code: uri.queryParameters['code'] ?? '',
    );
  }
  if (uri.path == '/pair' || uri.host == 'pair') {
    return (
      mode: PairingMode.temporary,
      identifier: uri.queryParameters['pairing_id'] ?? '',
      code: uri.queryParameters['code'] ?? '',
    );
  }
  return null;
}

class PairingScreen extends ConsumerStatefulWidget {
  const PairingScreen({super.key, required this.initialUri});
  final Uri initialUri;
  @override
  ConsumerState<PairingScreen> createState() => _PairingScreenState();
}

class _PairingScreenState extends ConsumerState<PairingScreen> {
  final setupId = TextEditingController();
  final activationCode = TextEditingController();
  final pairingId = TextEditingController();
  final pairingCode = TextEditingController();
  PairingMode mode = PairingMode.label;
  bool scanning = false;
  bool loading = false;
  String? error;
  @override
  void initState() {
    super.initState();
    _readUri(widget.initialUri);
  }

  String _normalized(String value) =>
      value.replaceAll(RegExp(r'[^A-Za-z0-9]'), '').toUpperCase();
  bool _readUri(Uri uri) {
    final link = parsePairingLink(uri);
    if (link == null) return false;
    mode = link.mode;
    if (link.mode == PairingMode.label) {
      setupId.text = link.identifier;
      activationCode.text = link.code;
    } else {
      pairingId.text = link.identifier;
      pairingCode.text = link.code;
    }
    return true;
  }

  Future<void> _handleBarcode(String raw) async {
    final uri = Uri.tryParse(raw);
    if (uri == null || !_readUri(uri)) {
      setState(() => error = AppText.of(context, 'invalid_pairing_qr'));
      return;
    }
    setState(() => scanning = false);
    if (mode == PairingMode.label) await claim();
  }

  Future<void> claim() async {
    final normalizedSetupId = _normalized(setupId.text);
    final normalizedActivation = _normalized(activationCode.text);
    if (mode == PairingMode.label &&
        (normalizedSetupId.length != 10 || normalizedActivation.length != 16)) {
      setState(() => error = AppText.of(context, 'invalid_activation'));
      return;
    }
    if (mode == PairingMode.temporary &&
        (pairingId.text.trim().isEmpty ||
            _normalized(pairingCode.text).length != 8)) {
      setState(() => error = AppText.of(context, 'invalid_temporary_pairing'));
      return;
    }
    setState(() {
      loading = true;
      error = null;
    });
    try {
      if (mode == PairingMode.label) {
        await ref
            .read(apiProvider)
            .claimStationActivation(normalizedSetupId, normalizedActivation);
      } else {
        await ref
            .read(apiProvider)
            .claimStation(pairingId.text.trim(), _normalized(pairingCode.text));
      }
      if (mounted) context.go('/stations');
    } catch (exception) {
      if (mounted) setState(() => error = exception.toString());
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  void dispose() {
    setupId.dispose();
    activationCode.dispose();
    pairingId.dispose();
    pairingCode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: PranaPageHeader(
      title: AppText.of(context, 'pair_station'),
      subtitle: 'STATION PAIRING',
    ),
    body: SafeArea(
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          const PranaLogo.mark(size: 72),
          const SizedBox(height: 16),
          Text(
            AppText.of(context, 'connect_station'),
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.w700,
              color: PranaTheme.navy,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            mode == PairingMode.label
                ? AppText.of(context, 'label_help')
                : AppText.of(context, 'temporary_help'),
            style: const TextStyle(color: PranaTheme.muted),
          ),
          const SizedBox(height: 18),
          SegmentedButton<PairingMode>(
            segments: [
              ButtonSegment(
                value: PairingMode.label,
                icon: const Icon(Icons.qr_code_2),
                label: Text(AppText.of(context, 'device_label')),
              ),
              ButtonSegment(
                value: PairingMode.temporary,
                icon: const Icon(Icons.timer_outlined),
                label: Text(AppText.of(context, 'temporary_code')),
              ),
            ],
            selected: {mode},
            onSelectionChanged:
                loading
                    ? null
                    : (selection) => setState(() {
                      mode = selection.first;
                      error = null;
                    }),
          ),
          const SizedBox(height: 18),
          if (scanning)
            ClipRRect(
              borderRadius: BorderRadius.circular(16),
              child: SizedBox(
                height: 280,
                child: MobileScanner(
                  onDetect: (capture) {
                    final raw = capture.barcodes.firstOrNull?.rawValue;
                    if (raw != null && !loading) _handleBarcode(raw);
                  },
                ),
              ),
            )
          else
            FilledButton.icon(
              onPressed: loading ? null : () => setState(() => scanning = true),
              icon: const Icon(Icons.qr_code_scanner),
              label: Text(AppText.of(context, 'scan_qr')),
            ),
          const SizedBox(height: 18),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children:
                    mode == PairingMode.label
                        ? [
                          TextField(
                            controller: setupId,
                            textCapitalization: TextCapitalization.characters,
                            maxLength: 10,
                            decoration: const InputDecoration(
                              labelText: 'Setup ID',
                              prefixIcon: Icon(Icons.tag),
                            ),
                          ),
                          const SizedBox(height: 10),
                          TextField(
                            controller: activationCode,
                            textCapitalization: TextCapitalization.characters,
                            inputFormatters: [ActivationCodeInputFormatter()],
                            decoration: InputDecoration(
                              labelText: 'Activation Code',
                              helperText: AppText.of(
                                context,
                                'activation_help',
                              ),
                              prefixIcon: const Icon(Icons.key_outlined),
                            ),
                          ),
                        ]
                        : [
                          TextField(
                            controller: pairingId,
                            decoration: const InputDecoration(
                              labelText: 'Pairing ID',
                              prefixIcon: Icon(Icons.tag),
                            ),
                          ),
                          const SizedBox(height: 10),
                          TextField(
                            controller: pairingCode,
                            textCapitalization: TextCapitalization.characters,
                            maxLength: 8,
                            decoration: InputDecoration(
                              labelText: AppText.of(context, 'temporary_code'),
                              prefixIcon: const Icon(Icons.timer_outlined),
                            ),
                          ),
                        ],
              ),
            ),
          ),
          if (error != null)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Text(
                error!,
                style: const TextStyle(color: Color(0xFFB12F40)),
              ),
            ),
          const SizedBox(height: 12),
          FilledButton(
            onPressed: loading ? null : claim,
            child: Text(loading ? '...' : AppText.of(context, 'pair_station')),
          ),
        ],
      ),
    ),
  );
}
