import 'package:prana_mobile/core/service_messages.dart';
import 'package:prana_mobile/app/di/radio_providers.dart';
import 'package:prana_mobile/app/di/station_providers.dart';
import 'package:prana_mobile/app/di/auth_providers.dart';
import 'package:prana_mobile/domain/radio/results.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:prana_mobile/domain/station/station.dart';
import 'package:prana_mobile/runtime/vhf/translation_speech.dart';

class StationRuntimeHost extends ConsumerStatefulWidget {
  const StationRuntimeHost({super.key, required this.child});

  final Widget child;

  @override
  ConsumerState<StationRuntimeHost> createState() => _StationRuntimeHostState();
}

class _StationRuntimeHostState extends ConsumerState<StationRuntimeHost>
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
    final id = ref.read(activeSpeechStationProvider);
    if (!foreground && id != null) {
      ref.read(stationSessionProvider(id)).tx.cancelRecordingForBackground();
    }
    ref.read(translationSpeechProvider).setForeground(foreground);
  }

  void _afterFrame(VoidCallback callback) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) callback();
    });
  }

  @override
  Widget build(BuildContext context) {
    var identityChanged = false;
    final auth = ref.watch(authStateProvider);
    final controller = ref.watch(translationSpeechProvider);
    if (auth.hasValue) {
      final nextUid = auth.value?.uid;
      if (_identityReady && nextUid != _uid) {
        identityChanged = true;
        _scheduledTrackingKey = null;
        _afterFrame(() {
          ref.read(activeSpeechStationProvider.notifier).state = null;
          controller.reset();
        });
      }
      _uid = nextUid;
      _identityReady = true;
    }

    final stationId = ref.watch(activeSpeechStationProvider);
    if (!identityChanged && _uid != null && stationId != null) {
      final stationValue = ref.watch(stationProvider(stationId));
      if (stationValue.hasValue) {
        final station = stationValue.value;
        if (station == null || !station.active) {
          _scheduledTrackingKey = null;
          if (!_missingStationHandled) {
            _missingStationHandled = true;
            _afterFrame(() {
              ref.read(activeSpeechStationProvider.notifier).state = null;
              controller.reset();
            });
          }
        } else {
          _missingStationHandled = false;
          ref.watch(stationSessionProvider(stationId));
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
          SnackBar(content: Text(localizedServiceMessage(context, warning))),
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
    final trackingKey = '$_uid|${station.id}|$dayKey';
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
      if (_scheduledTrackingKey != trackingKey ||
          ref.read(activeSpeechStationProvider) != station.id ||
          ref.read(authStateProvider).value?.uid != _uid) {
        return;
      }
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
