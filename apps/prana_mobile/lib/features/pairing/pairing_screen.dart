import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

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
      final end = (start + 4).clamp(0, limited.length);
      groups.add(limited.substring(start, end));
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
      setState(() => error = 'QR này không phải mã ghép PRANA ELEX.');
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
      setState(
        () => error = 'Nhập Setup ID 10 ký tự và Activation Code 16 ký tự.',
      );
      return;
    }
    if (mode == PairingMode.temporary &&
        (pairingId.text.trim().isEmpty ||
            _normalized(pairingCode.text).length != 8)) {
      setState(() => error = 'Nhập Pairing ID và mã tạm thời 8 ký tự.');
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
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Ghép trạm')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text(
              'Kết nối PRANA Station',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text(
              mode == PairingMode.label
                  ? 'Quét tem QR cố định được dán trên Raspberry Pi.'
                  : 'Dùng mã tạm thời do Laptop hoặc station cũ tạo ra.',
            ),
            const SizedBox(height: 20),
            SegmentedButton<PairingMode>(
              segments: const [
                ButtonSegment(
                  value: PairingMode.label,
                  icon: Icon(Icons.qr_code_2),
                  label: Text('Tem thiết bị'),
                ),
                ButtonSegment(
                  value: PairingMode.temporary,
                  icon: Icon(Icons.timer_outlined),
                  label: Text('Mã tạm thời'),
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
            const SizedBox(height: 20),
            if (scanning)
              ClipRRect(
                borderRadius: BorderRadius.circular(14),
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
                onPressed:
                    loading ? null : () => setState(() => scanning = true),
                icon: const Icon(Icons.qr_code_scanner),
                label: const Text('Mở camera quét QR'),
              ),
            const SizedBox(height: 24),
            if (mode == PairingMode.label) ...[
              TextField(
                controller: setupId,
                textCapitalization: TextCapitalization.characters,
                maxLength: 10,
                decoration: const InputDecoration(labelText: 'Setup ID'),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: activationCode,
                textCapitalization: TextCapitalization.characters,
                inputFormatters: [ActivationCodeInputFormatter()],
                decoration: const InputDecoration(
                  labelText: 'Activation Code',
                  helperText: '16 ký tự, tự động chia thành 4 nhóm',
                ),
              ),
            ] else ...[
              TextField(
                controller: pairingId,
                decoration: const InputDecoration(labelText: 'Pairing ID'),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: pairingCode,
                textCapitalization: TextCapitalization.characters,
                maxLength: 8,
                decoration: const InputDecoration(labelText: 'Mã tạm thời'),
              ),
            ],
            if (error != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text(
                  error!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ),
            FilledButton(
              onPressed: loading ? null : claim,
              child: Text(loading ? 'Đang ghép...' : 'Ghép trạm'),
            ),
          ],
        ),
      ),
    );
  }
}
