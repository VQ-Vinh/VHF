import 'dart:typed_data';
import 'package:prana_mobile/domain/radio/history_repository.dart';
import 'package:prana_mobile/domain/radio/results.dart';
import 'package:prana_mobile/domain/radio/tx/tx_draft.dart';
import 'package:prana_mobile/data/network/prana_api.dart';

class ApiHistoryRepository implements HistoryRepository {
  ApiHistoryRepository(this.api);
  final PranaApi api;
  @override
  Future<List<StationHistoryDay>> days(
    String stationId, {
    required bool tx,
    required int offset,
    String? timezone,
  }) =>
      tx
          ? api.txHistoryDays(
            stationId,
            timezoneOffsetMinutes: offset,
            timezone: timezone,
          )
          : api.stationHistoryDays(
            stationId,
            timezoneOffsetMinutes: offset,
            timezone: timezone,
          );
  @override
  Future<List<TranslationResult>> rxResults(
    String stationId,
    String date, {
    required int offset,
    String? timezone,
  }) => api.stationHistoryDayResults(
    stationId,
    date,
    timezoneOffsetMinutes: offset,
    timezone: timezone,
  );
  @override
  Future<List<TxDraft>> txJobs(
    String stationId,
    String date, {
    required int offset,
    String? timezone,
  }) => api.txHistoryDayJobs(
    stationId,
    date,
    timezoneOffsetMinutes: offset,
    timezone: timezone,
  );
  @override
  Future<Uint8List> txAudio(String stationId, String jobId) =>
      api.txHistoryAudio(stationId, jobId);
}
