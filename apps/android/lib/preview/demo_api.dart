import 'dart:typed_data';
import 'package:prana_mobile/data/network/prana_api.dart';
import 'package:prana_mobile/domain/radio/results.dart';
import 'package:prana_mobile/domain/radio/tx/tx_draft.dart';
import 'demo_store.dart';

/// Implements, never constructs, PranaApi: no Dio or Firebase is initialized.
class DemoApi implements PranaApi {
  DemoApi(this.store);
  final DemoStore store;

  @override
  Future<bool> health() async => true;
  @override
  Future<Map<String, dynamic>> account() async => Map.of(store.account);
  @override
  Future<List<Map<String, dynamic>>> countries() async => [
    {
      'code': 'VN',
      'name': 'Việt Nam',
      'timezones': ['Asia/Ho_Chi_Minh'],
    },
    {
      'code': 'SG',
      'name': 'Singapore',
      'timezones': ['Asia/Singapore'],
    },
    {
      'code': 'GB',
      'name': 'United Kingdom',
      'timezones': ['Europe/London'],
    },
  ];
  @override
  Future<Map<String, dynamic>> updateRegion({
    required String countryCode,
    String? timezone,
  }) async {
    final country = (await countries()).firstWhere(
      (item) => item['code'] == countryCode,
    );
    store.account['country_code'] = countryCode;
    store.account['timezone'] =
        timezone ?? (country['timezones'] as List).first;
    return account();
  }

  @override
  Future<List<Map<String, dynamic>>> plans() async => [
    {
      'id': 'demo-basic',
      'name': 'Basic (demo)',
      'availability': 'available',
      'audio_seconds_limit': 3600,
    },
    {
      'id': 'demo-pro',
      'name': 'Pro (demo)',
      'availability': 'available',
      'audio_seconds_limit': 36000,
    },
  ];
  @override
  Future<void> selectPlan(String planId) async {
    final plan = (await plans()).firstWhere((item) => item['id'] == planId);
    store.account['plan_id'] = planId;
    (store.account['usage'] as Map)['audio_seconds_limit'] =
        plan['audio_seconds_limit'];
  }

  @override
  Future<List<Map<String, dynamic>>> devices() async => List.of(store.devices);
  @override
  Future<void> revokeDevice(String deviceId) async =>
      store.devices.removeWhere((item) => item['id'] == deviceId);
  @override
  Future<List<Map<String, dynamic>>> stations() async =>
      store.stations.entries
          .map(
            (entry) => <String, dynamic>{
              ...entry.value,
              'station_id': entry.key,
            },
          )
          .toList();
  @override
  Future<void> removeStation(String stationId) async {
    store.stations.remove(stationId);
    store.notify();
  }

  @override
  Future<void> setDesiredState(
    String stationId, {
    bool? running,
    String? targetLanguage,
    String? captureMode,
    String? audioDeviceId,
    String? txAudioDeviceId,
    bool refreshCapabilities = false,
    bool retry = false,
  }) async => store.setDesired(
    stationId,
    running: running,
    targetLanguage: targetLanguage,
    captureMode: captureMode,
    audioDeviceId: audioDeviceId,
    txAudioDeviceId: txAudioDeviceId,
    refreshCapabilities: refreshCapabilities,
    retry: retry,
  );

  @override
  Future<List<TranslationResult>> stationResults(
    String stationId,
    String sessionId, {
    int limit = 1000,
  }) async =>
      (store.results[stationId] ?? [])
          .where((r) => r.sessionId == sessionId)
          .take(limit)
          .toList();
  @override
  Future<List<TranslationResult>> stationLiveResults(
    String stationId, {
    required int timezoneOffsetMinutes,
    String? timezone,
    int limit = 1000,
  }) async =>
      liveTranslationsForLocalDay(
        store.results[stationId] ?? [],
        store.clockNow,
      ).take(limit).toList();

  List<StationHistoryDay> _days(Iterable<DateTime> timestamps) {
    final groups = <String, List<DateTime>>{};
    for (final time in timestamps) {
      (groups[localDateKey(time)] ??= []).add(time);
    }
    return groups.entries.map((entry) {
        final times = entry.value..sort();
        return StationHistoryDay(
          date: DateTime.parse(entry.key),
          resultCount: times.length,
          firstResultAt: times.first,
          lastResultAt: times.last,
          locked: false,
        );
      }).toList()
      ..sort((a, b) => b.date.compareTo(a.date));
  }

  @override
  Future<List<StationHistoryDay>> stationHistoryDays(
    String stationId, {
    required int timezoneOffsetMinutes,
    String? timezone,
  }) async => _days((store.results[stationId] ?? []).map((r) => r.timestamp));
  @override
  Future<List<TranslationResult>> stationHistoryDayResults(
    String stationId,
    String date, {
    required int timezoneOffsetMinutes,
    String? timezone,
  }) async =>
      (store.results[stationId] ?? [])
          .where((r) => localDateKey(r.timestamp) == date)
          .toList();
  @override
  Future<List<StationHistoryDay>> txHistoryDays(
    String stationId, {
    required int timezoneOffsetMinutes,
    String? timezone,
  }) async => _days(
    store.drafts.values
        .where((d) => d.stationId == stationId && d.createdAt != null)
        .map((d) => d.createdAt!),
  );
  @override
  Future<List<TxDraft>> txHistoryDayJobs(
    String stationId,
    String date, {
    required int timezoneOffsetMinutes,
    String? timezone,
  }) async =>
      store.drafts.values
          .where(
            (d) =>
                d.stationId == stationId &&
                d.createdAt != null &&
                localDateKey(d.createdAt!) == date,
          )
          .toList();
  @override
  Future<Uint8List> txHistoryAudio(String stationId, String jobId) async =>
      Uint8List(0);
  @override
  Future<Uint8List> stationResultAudio(
    String stationId,
    String sessionId,
    String requestId,
  ) async => Uint8List(0);

  // Unsupported additions fail closed instead of reaching production services.
  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnsupportedError(
        'UI Preview: ${invocation.memberName} is not supported',
      );
}
