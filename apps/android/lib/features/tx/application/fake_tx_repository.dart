import '../domain/tx_draft.dart';
import 'tx_repository.dart';

class FakeTxRepository implements TxRepository {
  FakeTxRepository({
    this.processingDelay = const Duration(milliseconds: 700),
    this.transmissionDelay = const Duration(milliseconds: 900),
    this.processingError,
    this.transmissionError,
  });

  final Duration processingDelay;
  final Duration transmissionDelay;
  final Object? processingError;
  final Object? transmissionError;

  @override
  Future<TxDraft> processRecording(TxRecordingInput input) async {
    await Future<void>.delayed(processingDelay);
    if (processingError != null) throw processingError!;
    return TxDraft(
      id: 'tx-${DateTime.now().microsecondsSinceEpoch}',
      stationId: input.stationId,
      duration: input.duration,
      targetLanguage: input.targetLanguage,
      transcript: 'Please confirm the coordinates and report your status.',
      translation: _translationFor(input.targetLanguage),
    );
  }

  @override
  Future<void> confirmTransmission(TxDraft draft) async {
    await Future<void>.delayed(transmissionDelay);
    if (transmissionError != null) throw transmissionError!;
  }

  @override
  Future<void> cancelDraft(String draftId) async {}

  static String _translationFor(String language) => switch (language) {
    'vi' => 'Vui lòng xác nhận tọa độ và báo cáo trạng thái của bạn.',
    'zh' => '请确认坐标并报告您的状态。',
    'ja' => '座標を確認し、状況を報告してください。',
    'ko' => '좌표를 확인하고 현재 상태를 보고해 주세요.',
    _ => 'Please confirm the coordinates and report your status.',
  };
}
