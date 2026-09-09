import 'dart:typed_data';
import 'results.dart';
import 'tx/tx_draft.dart';

abstract interface class HistoryRepository {
  Future<List<StationHistoryDay>> days(
    String stationId, {
    required bool tx,
    required int offset,
    String? timezone,
  });
  Future<List<TranslationResult>> rxResults(
    String stationId,
    String date, {
    required int offset,
    String? timezone,
  });
  Future<List<TxDraft>> txJobs(
    String stationId,
    String date, {
    required int offset,
    String? timezone,
  });
  Future<Uint8List> txAudio(String stationId, String jobId);
}
