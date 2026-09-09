import 'package:prana_mobile/domain/radio/history_repository.dart';
import 'package:prana_mobile/domain/radio/results.dart';
import 'package:prana_mobile/domain/radio/tx/tx_draft.dart';
import 'dart:typed_data';

/// Loads RX/TX history through a replaceable data boundary.
class HistoryController {
  HistoryController(this.repository);
  final HistoryRepository repository;
  Future<List<StationHistoryDay>> stationHistoryDays(
    String id, {
    required int timezoneOffsetMinutes,
    String? timezone,
  }) => repository.days(
    id,
    tx: false,
    offset: timezoneOffsetMinutes,
    timezone: timezone,
  );
  Future<List<StationHistoryDay>> txHistoryDays(
    String id, {
    required int timezoneOffsetMinutes,
    String? timezone,
  }) => repository.days(
    id,
    tx: true,
    offset: timezoneOffsetMinutes,
    timezone: timezone,
  );
  Future<List<TranslationResult>> stationHistoryDayResults(
    String id,
    String date, {
    required int timezoneOffsetMinutes,
    String? timezone,
  }) => repository.rxResults(
    id,
    date,
    offset: timezoneOffsetMinutes,
    timezone: timezone,
  );
  Future<List<TxDraft>> txHistoryDayJobs(
    String id,
    String date, {
    required int timezoneOffsetMinutes,
    String? timezone,
  }) => repository.txJobs(
    id,
    date,
    offset: timezoneOffsetMinutes,
    timezone: timezone,
  );
  Future<Uint8List> txHistoryAudio(String id, String job) =>
      repository.txAudio(id, job);
}
