import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:prana_mobile/app/app.dart';
import 'package:prana_mobile/app/di/auth_providers.dart';
import 'package:prana_mobile/app/di/station_providers.dart';
import 'package:prana_mobile/app/di/radio_providers.dart';
import 'package:prana_mobile/app/di/history_providers.dart';
import 'package:prana_mobile/app/navigation/router.dart';
import 'demo_store.dart';
import 'demo_api.dart';
import 'demo_adapters.dart';
import 'preview_storage.dart';

/// Public harness also used by widget tests. Production bootstrap never imports it.
class PreviewApp extends StatefulWidget {
  const PreviewApp({super.key});
  @override
  State<PreviewApp> createState() => _PreviewAppState();
}

class _PreviewAppState extends State<PreviewApp> {
  int _generation = 0;
  @override
  Widget build(BuildContext context) => PreviewSession(
    key: ValueKey(_generation),
    onReset: () => setState(() => _generation++),
  );
}

class PreviewSession extends StatefulWidget {
  const PreviewSession({super.key, required this.onReset, this.store});
  final VoidCallback onReset;
  final DemoStore? store;
  @override
  State<PreviewSession> createState() => _PreviewSessionState();
}

class _PreviewSessionState extends State<PreviewSession> {
  late final store = widget.store ?? DemoStore();
  late final authentication = DemoAuthentication(onSignOut: store.dispose);
  late final api = DemoApi(store);
  late final storage = PreviewStorage();
  @override
  Widget build(BuildContext context) => ProviderScope(
    overrides: [
      // Fail closed if a future screen bypasses the service boundary.
      authProvider.overrideWith(
        (ref) => throw StateError('Firebase disabled in UI Preview'),
      ),
      firestoreProvider.overrideWith(
        (ref) => throw StateError('Firestore disabled in UI Preview'),
      ),
      authStateProvider.overrideWith((ref) => authentication.watch()),
      authenticationServiceProvider.overrideWithValue(authentication),
      apiProvider.overrideWithValue(api),
      apiHealthProvider.overrideWith((ref) => Stream.value(true)),
      liveResultsProvider.overrideWith(
        (ref, query) => store.watchLiveResults(query.stationId),
      ),
      secureStorageProvider.overrideWithValue(storage),
      stationRepositoryProvider.overrideWith(
        (ref) => DemoStationRepository(store),
      ),
      txRecorderProvider.overrideWithValue(DemoRecorder.new),
      txRepositoryProvider.overrideWith((ref) => () => DemoTxRepository(store)),
      speechEngineProvider.overrideWith((ref) {
        final engine = DemoPlayback();
        ref.onDispose(engine.dispose);
        return engine;
      }),
      sourceAudioEngineProvider.overrideWith((ref) {
        final engine = DemoPlayback();
        ref.onDispose(engine.dispose);
        return engine;
      }),
      historyAudioEngineProvider.overrideWithValue(DemoPlayback.new),
      signInPageProvider.overrideWithValue(
        (_) => _DemoEnded(onEnter: widget.onReset),
      ),
      pairingPageProvider.overrideWithValue(
        (_, _) => const _PairingUnavailable(),
      ),
    ],
    child: PranaMobileApp(
      frameBuilder:
          (context, child) => FocusTraversalGroup(
            policy: WidgetOrderTraversalPolicy(),
            child: _PreviewFrame(onReset: widget.onReset, child: child),
          ),
    ),
  );
  @override
  void dispose() {
    authentication.dispose();
    store.dispose();
    super.dispose();
  }
}

class _PreviewFrame extends ConsumerStatefulWidget {
  const _PreviewFrame({required this.child, required this.onReset});
  final Widget child;
  final VoidCallback onReset;
  @override
  ConsumerState<_PreviewFrame> createState() => _PreviewFrameState();
}

class _PreviewFrameState extends ConsumerState<_PreviewFrame> {
  double scale = 1;
  @override
  Widget build(BuildContext context) {
    final vi = Localizations.localeOf(context).languageCode == 'vi';
    final actionStyle = TextButton.styleFrom(
      minimumSize: const Size(48, 48),
      visualDensity: VisualDensity.standard,
      tapTargetSize: MaterialTapTargetSize.padded,
    );
    return Column(
      children: [
        Material(
          color: Theme.of(context).colorScheme.secondaryContainer,
          child: SafeArea(
            bottom: false,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      vi
                          ? 'UI Preview — dữ liệu mô phỏng'
                          : 'UI Preview — simulated data',
                      style: Theme.of(context).textTheme.labelMedium,
                    ),
                  ),
                  TextButton(
                    key: const ValueKey('preview-text-scale'),
                    style: actionStyle,
                    onPressed:
                        () =>
                            setState(() => scale = scale == 2 ? 1 : scale + .5),
                    child: Semantics(
                      label: vi ? 'Cỡ chữ' : 'Text scale',
                      child: Text('$scale×'),
                    ),
                  ),
                  TextButton.icon(
                    key: const ValueKey('preview-reset'),
                    style: actionStyle,
                    onPressed: widget.onReset,
                    icon: const Icon(Icons.restart_alt),
                    label: Text(vi ? 'Đặt lại' : 'Reset'),
                  ),
                ],
              ),
            ),
          ),
        ),
        Expanded(
          child: MediaQuery(
            data: MediaQuery.of(
              context,
            ).copyWith(textScaler: TextScaler.linear(scale)),
            child: widget.child,
          ),
        ),
      ],
    );
  }
}

class _DemoEnded extends StatelessWidget {
  const _DemoEnded({required this.onEnter});
  final VoidCallback onEnter;
  @override
  Widget build(BuildContext context) {
    final vi = Localizations.localeOf(context).languageCode == 'vi';
    return Scaffold(
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(vi ? 'Phiên demo đã kết thúc' : 'Demo session ended'),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: onEnter,
                child: Text(vi ? 'Vào lại demo' : 'Enter demo'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _PairingUnavailable extends StatelessWidget {
  const _PairingUnavailable();
  @override
  Widget build(BuildContext context) {
    final vi = Localizations.localeOf(context).languageCode == 'vi';
    return Scaffold(
      appBar: AppBar(
        leading: BackButton(onPressed: () => context.go('/stations')),
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(
            vi
                ? 'Ghép Station chưa hỗ trợ trong UI Preview.'
                : 'Station pairing is unavailable in UI Preview.',
          ),
        ),
      ),
    );
  }
}
