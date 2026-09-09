import 'package:prana_mobile/l10n/app_localizations.dart';
import '../control/presentation/control_tab.dart';
import 'package:prana_mobile/core/responsive.dart';
import 'dart:async';
import 'package:prana_mobile/app/di/telemetry_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:prana_mobile/app/di/account_providers.dart';
import 'package:prana_mobile/app/di/auth_providers.dart';
import 'package:prana_mobile/app/di/station_providers.dart';
import 'package:prana_mobile/app/di/radio_providers.dart';
import 'package:prana_mobile/features/station/dashboard/presentation/dashboard_tab.dart';
import 'package:prana_mobile/features/station/radio/presentation/live_screen.dart';
import 'package:prana_mobile/features/station/history/history_screen.dart';
import 'package:prana_mobile/features/station/settings/station_settings_screen.dart';
import 'station_tab.dart';

class StationWorkspaceScreen extends ConsumerStatefulWidget {
  const StationWorkspaceScreen({
    super.key,
    required this.stationId,
    required this.page,
  });
  final String stationId;
  final StationPage page;
  @override
  ConsumerState<StationWorkspaceScreen> createState() =>
      _StationWorkspaceState();
}

class _StationWorkspaceState extends ConsumerState<StationWorkspaceScreen> {
  final _visited = <StationPage>{};
  final _historyKey = GlobalKey<HistoryScreenState>();
  bool _leaving = false;
  StationPage _settingsReturn = StationPage.dashboard;
  @override
  void initState() {
    super.initState();
    _visited.add(widget.page);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      ref.read(activeSpeechStationProvider.notifier).state = widget.stationId;
      ref.invalidate(accountProvider);
    });
  }

  @override
  void didUpdateWidget(covariant StationWorkspaceScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    _visited.add(widget.page);
  }

  void _select(StationPage tab) {
    if (tab == widget.page) return;
    if (tab == StationPage.settings) _settingsReturn = widget.page;
    // Ends HTT synchronously before navigation; the processing Future belongs
    // to the Station session and may complete while any tab is visible.
    unawaited(
      ref.read(stationSessionProvider(widget.stationId)).tx.stopRecording(),
    );
    context.replace('/stations/${widget.stationId}/${tab.name}');
  }

  Future<void> _back() async {
    if (_leaving) return;
    if (widget.page == StationPage.history &&
        (_historyKey.currentState?.backToDays() ?? false)) {
      return;
    }
    if (widget.page == StationPage.history) {
      _select(StationPage.live);
      return;
    }
    if (widget.page == StationPage.settings) {
      _select(_settingsReturn);
      return;
    }
    _leaving = true;
    try {
      final tx = ref.read(stationSessionProvider(widget.stationId)).tx;
      if (tx.state.requiresLeaveConfirmation) {
        final discard = await showDialog<bool>(
          context: context,
          builder:
              (context) => AlertDialog(
                scrollable: true,
                title: Text(AppLocalizations.of(context).txDiscardTitle),
                content: Text(AppLocalizations.of(context).txDiscardBody),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.pop(context, false),
                    child: Text(AppLocalizations.of(context).close),
                  ),
                  FilledButton(
                    onPressed: () => Navigator.pop(context, true),
                    child: Text(AppLocalizations.of(context).txDiscard),
                  ),
                ],
              ),
        );
        if (discard != true) return;
        await tx.cancelDraft();
      }
      if (!mounted) return;
      if (context.canPop()) {
        context.pop();
      } else {
        context.go('/stations');
      }
    } finally {
      _leaving = false;
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authStateProvider);
    final station = ref.watch(stationProvider(widget.stationId));
    if (station.hasError) {
      return ResponsiveScaffold(
        appBar: ResponsiveHeader(),
        body: Center(
          child: TextButton(
            onPressed: () => ref.invalidate(stationProvider(widget.stationId)),
            child: Text(AppLocalizations.of(context).retry),
          ),
        ),
      );
    }
    if (!auth.hasValue || auth.value == null || !station.hasValue) {
      return const ResponsiveScaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }
    if (station.value == null || !station.value!.active) {
      return ResponsiveScaffold(
        appBar: ResponsiveHeader(),
        body: Center(
          child: Text(AppLocalizations.of(context).stationUnavailable),
        ),
      );
    }
    final runtime = ref.watch(stationRuntimeStateProvider(widget.stationId));
    final primary = widget.page.primaryTab;
    final labels = [
      AppLocalizations.of(context).dashboard,
      'Control',
      'Live VHF',
    ];
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) _back();
      },
      child: ResponsiveScaffold(
        maxWidth: ContentWidth.dashboard,
        appBar: ResponsiveHeader(
          toolbarHeight:
              MediaQuery.textScalerOf(context).scale(44).clamp(56, 120) + 8,
          leading: IconButton(
            key: const ValueKey('workspace-back'),
            onPressed: _back,
            icon: const Icon(Icons.arrow_back),
            tooltip: MaterialLocalizations.of(context).backButtonTooltip,
          ),
          actions: [
            if (widget.page != StationPage.settings)
              IconButton(
                key: const ValueKey('station-settings-button'),
                tooltip: AppLocalizations.of(context).stationSettings,
                onPressed: () => _select(StationPage.settings),
                constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
                icon: const Icon(Icons.settings_outlined),
              ),
          ],
          title: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(switch (widget.page) {
                StationPage.history => AppLocalizations.of(context).history,
                StationPage.settings =>
                  AppLocalizations.of(context).stationSettings,
                _ => runtime.station?.name ?? 'PRANA ELEX',
              }),
              Text(
                (runtime.online
                    ? AppLocalizations.of(context).stationOnline
                    : AppLocalizations.of(context).stationOffline),
                style: const TextStyle(fontSize: 12),
              ),
            ],
          ),
        ),
        body: Column(
          children: [
            if (primary != null)
              Material(
                color: Theme.of(context).colorScheme.surface,
                child: SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      for (final tab in StationTab.values)
                        Semantics(
                          selected: primary == tab,
                          button: true,
                          child: InkWell(
                            key: ValueKey('station-tab-${tab.name}'),
                            onTap: () => _select(tab.page),
                            child: Container(
                              constraints: const BoxConstraints(minHeight: 48),
                              padding: const EdgeInsets.symmetric(
                                horizontal: 20,
                                vertical: 14,
                              ),
                              decoration: BoxDecoration(
                                border: Border(
                                  bottom: BorderSide(
                                    width: 3,
                                    color:
                                        primary == tab
                                            ? Theme.of(
                                              context,
                                            ).colorScheme.primary
                                            : Colors.transparent,
                                  ),
                                ),
                              ),
                              child: Text(
                                labels[tab.index],
                                style: TextStyle(
                                  fontWeight:
                                      primary == tab
                                          ? FontWeight.w800
                                          : FontWeight.w500,
                                ),
                              ),
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
              ),
            Expanded(
              child: IndexedStack(
                index: widget.page.index,
                children: [
                  for (final tab in StationPage.values)
                    TickerMode(
                      enabled: widget.page == tab,
                      child:
                          !_visited.contains(tab)
                              ? const SizedBox.shrink()
                              : switch (tab) {
                                StationPage.dashboard => DashboardTab(
                                  stationId: widget.stationId,
                                  stationOnline: runtime.online,
                                ),
                                StationPage.control => ControlTab(
                                  key: ValueKey(
                                    'control-${auth.value!.uid}-${widget.stationId}',
                                  ),
                                  stationId: widget.stationId,
                                  active: widget.page == tab,
                                ),
                                StationPage.live => LiveScreen(
                                  stationId: widget.stationId,
                                  active: widget.page == tab,
                                  embedded: true,
                                  onHistory: () => _select(StationPage.history),
                                ),
                                StationPage.history => HistoryScreen(
                                  key: _historyKey,
                                  stationId: widget.stationId,
                                  embedded: true,
                                  active: widget.page == tab,
                                ),
                                StationPage.settings => StationSettingsScreen(
                                  stationId: widget.stationId,
                                  embedded: true,
                                ),
                              },
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
