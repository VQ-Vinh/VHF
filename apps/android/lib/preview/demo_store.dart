import 'dart:async';
import 'package:prana_mobile/domain/station/station.dart';
import 'package:prana_mobile/domain/radio/results.dart';
import 'package:prana_mobile/domain/radio/tx/tx_draft.dart';

/// Session-only source of truth. No network, plugins or production configuration.
class DemoStore {
  DemoStore({DateTime Function()? clock, bool ticking = true})
    : clock = clock ?? DateTime.now {
    for (final id in ['demo-online', 'demo-offline']) {
      stations[id] = {
        'name': id == 'demo-online' ? 'VINH Station' : 'Harbor Station',
        'platform': 'Raspberry Pi (demo)',
        'storage_folder': id.toUpperCase(),
        'active': true,
        'capture_state': 'idle',
        'session_id': '$id-session',
        'sequence': 0,
        'desired_state': <String, dynamic>{
          'running': false,
          'target_language': 'vi',
          'generation': 0,
          'capture_mode': 'device',
          'audio_device_id': 'demo-usb',
          'tx_audio_device_id': 'demo-usb',
        },
        'observed_generation': 0,
        'active_audio_device_id': 'demo-usb',
        'active_tx_audio_device_id': 'demo-usb',
        'last_seen_at': clockNow.subtract(
          Duration(minutes: id == 'demo-online' ? 0 : 60),
        ),
        'capabilities': {
          'capability_hash': 'demo-v1',
          'capture_modes': ['device'],
          'audio_devices': [
            {
              'id': 'demo-usb',
              'name': 'USB VHF (demo)',
              'mode': 'device',
              'input_channels': 1,
              'output_channels': 2,
              'sample_rate': 48000,
              'host_api': 'Demo',
            },
            {
              'id': 'demo-usb-alt',
              'name': 'USB alternate (demo)',
              'mode': 'device',
              'input_channels': 1,
              'output_channels': 2,
              'sample_rate': 48000,
              'host_api': 'Demo',
            },
          ],
          'storage_path': '/demo/audio',
          'updated_at': clockNow,
        },
      };
      results[id] = [];
      for (var day = 2; day >= 0; day--) {
        for (var i = 0; i < 3; i++) {
          addResult(id, clockNow.subtract(Duration(days: day, minutes: 3 - i)));
        }
        final job = TxDraft(
          id: '$id-history-$day',
          stationId: id,
          duration: const Duration(seconds: 5),
          targetLanguage: 'en',
          transcript: 'Xin phép cập cảng.',
          translation: 'Requesting permission to enter the harbor.',
          detectedLanguage: 'vi',
          status: 'completed',
          outputAvailable: true,
          createdAt: clockNow.subtract(Duration(days: day, minutes: 5)),
        );
        drafts[job.id] = job;
      }
    }
    if (ticking) {
      _timer = Timer.periodic(const Duration(seconds: 1), (_) => tick());
    }
  }

  final DateTime Function() clock;
  DateTime get clockNow => clock();
  final stations = <String, Map<String, dynamic>>{};
  final results = <String, List<TranslationResult>>{};
  final drafts = <String, TxDraft>{};
  final activeDrafts = <String, String>{};
  final confirmedAt = <String, DateTime>{};
  final changes = StreamController<void>.broadcast(sync: true);
  final account = <String, dynamic>{
    'country_code': 'VN',
    'timezone': 'Asia/Ho_Chi_Minh',
    'plan_id': 'demo-pro',
    'status': 'active',
    'usage': {'used_audio_seconds': 180, 'audio_seconds_limit': 36000},
    'entitlements': {
      'history_past_days': 30,
      'max_concurrency': 2,
      'tx_max_recording_seconds': 60,
    },
  };
  final devices = <Map<String, dynamic>>[
    {'id': 'demo-browser', 'name': 'Preview browser', 'platform': 'Web demo'},
  ];
  Timer? _timer;
  bool disposed = false;
  int _ticks = 0;
  int commandCount = 0;
  int projectionSubscriptions = 0;
  int resultsSubscriptions = 0;
  int _resultId = 0;

  List<StationModel> get stationModels =>
      stations.entries
          .map((entry) => StationModel.fromMap(entry.key, entry.value))
          .toList();

  void notify() {
    if (!disposed) changes.add(null);
  }

  Stream<List<TranslationResult>> watchLiveResults(String id) =>
      Stream.multi((controller) {
        resultsSubscriptions++;
        void emit() => controller.addSync(
          liveTranslationsForLocalDay(results[id] ?? [], clockNow),
        );
        final sub = changes.stream.listen((_) => emit());
        emit();
        controller.onCancel = () {
          resultsSubscriptions--;
          return sub.cancel();
        };
      });

  void addResult(String id, DateTime time) {
    final n = ++_resultId;
    const samples = [
      (
        'Harbor control, this is vessel Prana. Requesting entry.',
        'Trạm cảng, đây là tàu Prana. Xin phép vào cảng.',
      ),
      (
        'Wind from the northeast, five knots. Maintain course.',
        'Gió Đông Bắc, năm hải lý mỗi giờ. Giữ hướng.',
      ),
      (
        'Copy that. Standing by on channel sixteen.',
        'Đã rõ. Đang trực trên kênh mười sáu.',
      ),
    ];
    final sample = samples[n % samples.length];
    results[id]!.add(
      TranslationResult(
        requestId: 'demo-rx-$n',
        sessionId: '$id-session',
        sequence: n,
        transcript: sample.$1,
        translation: sample.$2,
        language: 'en',
        targetLanguage: 'vi',
        confidence: .98,
        timestamp: time,
      ),
    );
    stations[id]!['sequence'] = n;
  }

  void tick() {
    if (disposed) return;
    _ticks++;
    final online = stations['demo-online'];
    if (online != null) {
      online['last_seen_at'] = clockNow;
      if ((online['desired_state'] as Map)['running'] == true &&
          _ticks % 5 == 0) {
        addResult('demo-online', clockNow);
      }
    }
    for (final entry in confirmedAt.entries.toList()) {
      final elapsed = clockNow.difference(entry.value).inSeconds;
      final draft = drafts[entry.key]!;
      drafts[entry.key] = draft.copyWith(
        status:
            elapsed >= 6
                ? 'completed'
                : elapsed >= 2
                ? 'transmitting'
                : 'queued',
      );
      if (elapsed >= 6) confirmedAt.remove(entry.key);
    }
    notify();
  }

  void setDesired(
    String id, {
    bool? running,
    String? targetLanguage,
    String? captureMode,
    String? audioDeviceId,
    String? txAudioDeviceId,
    bool refreshCapabilities = false,
    bool retry = false,
  }) {
    if (disposed) return;
    final station = stations[id];
    if (station == null) throw StateError('Demo Station not found');
    commandCount++;
    final desired = station['desired_state'] as Map<String, dynamic>;
    if (running != null) desired['running'] = running;
    if (targetLanguage != null) desired['target_language'] = targetLanguage;
    if (captureMode != null) desired['capture_mode'] = captureMode;
    if (audioDeviceId != null) desired['audio_device_id'] = audioDeviceId;
    if (txAudioDeviceId != null) {
      desired['tx_audio_device_id'] = txAudioDeviceId;
    }
    desired['generation'] = (desired['generation'] as int) + 1;
    if (retry) {
      desired['retry_generation'] =
          (desired['retry_generation'] as int? ?? 0) + 1;
    }
    if (refreshCapabilities) {
      desired['capability_refresh_generation'] =
          (desired['capability_refresh_generation'] as int? ?? 0) + 1;
      (station['capabilities'] as Map)['updated_at'] = clockNow;
      (station['capabilities'] as Map)['capability_hash'] =
          'demo-${desired['generation']}';
    }
    station['observed_generation'] = desired['generation'];
    station['capture_state'] = desired['running'] == true ? 'running' : 'idle';
    station['active_capture_mode'] = desired['capture_mode'];
    station['active_audio_device_id'] = desired['audio_device_id'];
    station['active_tx_audio_device_id'] = desired['tx_audio_device_id'];
    notify();
  }

  void dispose() {
    if (disposed) return;
    disposed = true;
    _timer?.cancel();
    changes.close();
  }
}
