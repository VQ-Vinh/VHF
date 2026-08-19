import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/localization.dart';
import '../../models/station.dart';
import '../../providers.dart';
import '../../services/translation_speech.dart';

class TranslationSpeechHost extends ConsumerStatefulWidget {
  const TranslationSpeechHost({super.key, required this.child});

  final Widget child;

  @override
  ConsumerState<TranslationSpeechHost> createState() =>
      _TranslationSpeechHostState();
}

class _TranslationSpeechHostState extends ConsumerState<TranslationSpeechHost>
    with WidgetsBindingObserver {
  String? _uid;
  bool _identityReady = false;
  String? _warningShown;
  bool _missingStationHandled = false;
  String? _scheduledTrackingKey;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    final foreground = state == AppLifecycleState.resumed;
    ref.read(translationSpeechProvider).setForeground(foreground);
  }

  void _afterFrame(VoidCallback callback) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) callback();
    });
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authStateProvider);
    final controller = ref.watch(translationSpeechProvider);
    if (auth.hasValue) {
      final nextUid = auth.value?.uid;
      if (_identityReady && nextUid != _uid) {
        _afterFrame(() {
          ref.read(activeSpeechStationProvider.notifier).state = null;
          controller.reset();
        });
      }
      _uid = nextUid;
      _identityReady = true;
    }

    final stationId = ref.watch(activeSpeechStationProvider);
    if (_uid != null && stationId != null) {
      final stationValue = ref.watch(stationProvider(stationId));
      if (stationValue.hasValue) {
        final station = stationValue.value;
        if (station == null || !station.active) {
          if (!_missingStationHandled) {
            _missingStationHandled = true;
            _afterFrame(() {
              ref.read(activeSpeechStationProvider.notifier).state = null;
              controller.reset();
            });
          }
        } else {
          _missingStationHandled = false;
          _trackStation(controller, station);
        }
      }
    }

    final warning = controller.warningKey;
    if (warning != null && warning != _warningShown) {
      _warningShown = warning;
      _afterFrame(() {
        final messenger = ScaffoldMessenger.maybeOf(context);
        messenger?.showSnackBar(
          SnackBar(content: Text(AppText.of(context, warning))),
        );
        controller.clearWarning();
        _warningShown = null;
      });
    }

    return widget.child;
  }

  void _trackStation(
    TranslationSpeechController controller,
    StationModel station,
  ) {
    final now = ref.watch(stationClockProvider).value ?? DateTime.now();
    final dayKey = localDateKey(now);
    final trackingKey = '${station.id}|$dayKey';
    _scheduledTrackingKey = trackingKey;
    List<TranslationResult>? values;
    final results = ref.watch(
      liveResultsProvider((
        stationId: station.id,
        localDate: dayKey,
        timezoneOffsetMinutes: now.timeZoneOffset.inMinutes,
        timezone: ref.read(userRegionProvider).timezoneName,
      )),
    );
    if (results.hasValue) {
      values = results.value ?? const <TranslationResult>[];
    }
    _afterFrame(() {
      if (_scheduledTrackingKey != trackingKey) return;
      controller.trackStation(
        station.id,
        dayKey,
        fallbackSessionId: station.sessionId,
      );
      if (values != null) {
        controller.ingest(
          values,
          fallbackLanguage: station.desired.targetLanguage,
        );
      }
    });
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }
}
