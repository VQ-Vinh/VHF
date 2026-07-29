import '../domain/tx_draft.dart';
import '../domain/tx_failure.dart';
import '../domain/tx_phase.dart';

class TxState {
  const TxState({
    this.phase = TxPhase.idle,
    this.duration = Duration.zero,
    this.targetLanguage = 'vi',
    this.draft,
    this.failure,
  });

  final TxPhase phase;
  final Duration duration;
  final String targetLanguage;
  final TxDraft? draft;
  final TxFailure? failure;

  bool get canChangeLanguage => phase == TxPhase.idle;
  bool get canStartRecording => phase == TxPhase.idle;
  bool get requiresLeaveConfirmation => phase.isDraftActive;

  TxState copyWith({
    TxPhase? phase,
    Duration? duration,
    String? targetLanguage,
    TxDraft? draft,
    TxFailure? failure,
    bool clearDraft = false,
    bool clearFailure = false,
  }) => TxState(
    phase: phase ?? this.phase,
    duration: duration ?? this.duration,
    targetLanguage: targetLanguage ?? this.targetLanguage,
    draft: clearDraft ? null : draft ?? this.draft,
    failure: clearFailure ? null : failure ?? this.failure,
  );
}
