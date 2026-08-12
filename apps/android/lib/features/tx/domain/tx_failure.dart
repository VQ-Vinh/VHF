enum TxFailure {
  stationOffline,
  stationOfflineDuringTx,
  busy,
  channelBusy,
  expired,
  processingFailed,
  recordingTooLong,
  transmissionFailed,
}

extension TxFailureTextKey on TxFailure {
  String get textKey => switch (this) {
    TxFailure.stationOffline => 'tx_station_offline',
    TxFailure.stationOfflineDuringTx => 'tx_station_offline_during_tx',
    TxFailure.busy => 'tx_station_busy',
    TxFailure.channelBusy => 'tx_channel_busy',
    TxFailure.expired => 'tx_expired',
    TxFailure.processingFailed => 'tx_processing_failed',
    TxFailure.recordingTooLong => 'tx_audio_too_long',
    TxFailure.transmissionFailed => 'tx_transmission_failed',
  };
}
