enum TxFailure {
  stationOffline,
  stationOfflineDuringTx,
  pttUnavailable,
  busy,
  channelBusy,
  expired,
  processingFailed,
  recordingTooLong,
  outputTooLong,
  synthesisTimeout,
  playbackTimeout,
  transmissionFailed,
}

extension TxFailureTextKey on TxFailure {
  String get textKey => switch (this) {
    TxFailure.stationOffline => 'tx_station_offline',
    TxFailure.stationOfflineDuringTx => 'tx_station_offline_during_tx',
    TxFailure.pttUnavailable => 'tx_ptt_unavailable',
    TxFailure.busy => 'tx_station_busy',
    TxFailure.channelBusy => 'tx_channel_busy',
    TxFailure.expired => 'tx_expired',
    TxFailure.processingFailed => 'tx_processing_failed',
    TxFailure.recordingTooLong => 'tx_audio_too_long',
    TxFailure.outputTooLong => 'tx_output_too_long',
    TxFailure.synthesisTimeout => 'tx_synthesis_timeout',
    TxFailure.playbackTimeout => 'tx_playback_timeout',
    TxFailure.transmissionFailed => 'tx_transmission_failed',
  };
}
