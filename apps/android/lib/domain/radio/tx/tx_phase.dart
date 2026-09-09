enum TxPhase {
  idle,
  recording,
  processing,
  reviewReady,
  queued,
  transmitting,
  completed,
  stationOffline,
  busy,
  channelBusy,
  expired,
  failed,
}

extension TxPhaseState on TxPhase {
  bool get isDraftActive =>
      this == TxPhase.recording ||
      this == TxPhase.processing ||
      this == TxPhase.reviewReady;

  bool get isTerminal =>
      this == TxPhase.completed ||
      this == TxPhase.stationOffline ||
      this == TxPhase.busy ||
      this == TxPhase.channelBusy ||
      this == TxPhase.expired ||
      this == TxPhase.failed;
}
