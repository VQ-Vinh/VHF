import 'package:flutter/widgets.dart';
import 'package:prana_mobile/l10n/app_localizations.dart';

/// Maps service failure/status codes at the presentation boundary.
String localizedServiceMessage(BuildContext context, String code) {
  final l10n = AppLocalizations.of(context);
  return switch (code) {
    'rx_audio_input_not_found' => l10n.rxAudioInputNotFound,
    'rx_start_failed' => l10n.rxStartFailed,
    'auth_invalid_email' => l10n.authInvalidEmail,
    'auth_invalid_credentials' => l10n.authInvalidCredentials,
    'auth_email_in_use' => l10n.authEmailInUse,
    'auth_weak_password' => l10n.authWeakPassword,
    'auth_user_disabled' => l10n.authUserDisabled,
    'auth_too_many_requests' => l10n.authTooManyRequests,
    'auth_network_error' => l10n.authNetworkError,
    'auth_google_error' => l10n.authGoogleError,
    'auth_unknown_error' => l10n.authUnknownError,
    'verification_still_pending' => l10n.verificationStillPending,
    'verification_resent' => l10n.verificationResent,
    'device_scan_changed' => l10n.deviceScanChanged,
    'device_scan_unchanged' => l10n.deviceScanUnchanged,
    'device_scan_timeout' => l10n.deviceScanTimeout,
    'settings_sync_delayed' => l10n.settingsSyncDelayed,
    'error_station_not_paired' => l10n.errorStationNotPaired,
    'error_station_revoked' => l10n.errorStationRevoked,
    'error_station_limit_reached' => l10n.errorStationLimitReached,
    'error_activation_invalid' => l10n.errorActivationInvalid,
    'error_station_already_claimed' => l10n.errorStationAlreadyClaimed,
    'error_connection_timeout' => l10n.errorConnectionTimeout,
    'error_request_timeout' => l10n.errorRequestTimeout,
    'error_api_unreachable' => l10n.errorApiUnreachable,
    'error_request_failed' => l10n.errorRequestFailed,
    'tts_language_unavailable' => l10n.ttsLanguageUnavailable,
    'tts_playback_error' => l10n.ttsPlaybackError,
    'tx_station_offline' => l10n.txStationOffline,
    'tx_station_offline_during_tx' => l10n.txStationOfflineDuringTx,
    'tx_ptt_unavailable' => l10n.txPttUnavailable,
    'tx_station_busy' => l10n.txStationBusy,
    'tx_channel_busy' => l10n.txChannelBusy,
    'tx_expired' => l10n.txExpired,
    'tx_processing_failed' => l10n.txProcessingFailed,
    'tx_audio_too_long' => l10n.txAudioTooLong,
    'tx_output_too_long' => l10n.txOutputTooLong,
    'tx_synthesis_timeout' => l10n.txSynthesisTimeout,
    'tx_playback_timeout' => l10n.txPlaybackTimeout,
    'tx_transmission_failed' => l10n.txTransmissionFailed,
    _ => code,
  };
}

String txStatusLabel(AppLocalizations l10n, String status) => switch (status) {
  'synthesizing' => l10n.txStatusSynthesizing,
  'queued' => l10n.txStatusQueued,
  'claimed' => l10n.txStatusClaimed,
  'transmitting' => l10n.txStatusTransmitting,
  'completed' => l10n.txStatusCompleted,
  'failed' => l10n.txStatusFailed,
  _ => status,
};
