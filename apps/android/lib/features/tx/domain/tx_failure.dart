enum TxFailure {
  stationOffline,
  busy,
  channelBusy,
  expired,
  processingFailed,
  transmissionFailed,
}

extension TxFailureTextKey on TxFailure {
  String get textKey => switch (this) {
    TxFailure.stationOffline => 'tx_station_offline',
    TxFailure.busy => 'tx_station_busy',
    TxFailure.channelBusy => 'tx_channel_busy',
    TxFailure.expired => 'tx_expired',
    TxFailure.processingFailed => 'tx_processing_failed',
    TxFailure.transmissionFailed => 'tx_transmission_failed',
  };
}
