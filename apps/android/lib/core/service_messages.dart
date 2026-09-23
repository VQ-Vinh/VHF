import 'package:dio/dio.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/widgets.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:prana_mobile/data/auth/authentication_service.dart';
import 'package:prana_mobile/data/network/prana_api.dart';
import 'package:prana_mobile/l10n/app_localizations.dart';

/// User-facing text for any caught error. Never shows the raw error: exception
/// text, server messages and Firebase codes are for logs, not operators.
String localizedErrorMessage(BuildContext context, Object? error) =>
    localizedServiceMessage(context, errorMessageKey(error));

String errorMessageKey(Object? error) => switch (error) {
  PranaApiFailure(:final messageKey) => messageKey,
  DioException() => PranaApiFailure.fromDio(error).messageKey,
  final Object auth
      when auth is FirebaseAuthException || auth is GoogleSignInException =>
    authenticationErrorKey(auth),
  FirebaseException(code: 'unavailable') => 'error_api_unreachable',
  _ => 'error_request_failed',
};

/// Maps an error the Station reported (a code, or `CODE: exception text`).
String stationErrorKey(
  String raw, {
  String fallback = 'error_station_processing',
}) => switch (raw.split(':').first.trim()) {
  'AUDIO_DEVICE_UNAVAILABLE' ||
  'AUDIO_INPUT_DEVICE_NOT_FOUND' => 'rx_audio_input_not_found',
  final code => PranaApiFailure.fromCode(code)?.messageKey ?? fallback,
};

/// Maps service failure/status codes at the presentation boundary. An unknown
/// code falls back to generic text rather than being shown verbatim.
String localizedServiceMessage(BuildContext context, String code) {
  final l10n = AppLocalizations.of(context);
  return switch (code) {
    'rx_audio_input_not_found' => l10n.rxAudioInputNotFound,
    'rx_start_failed' => l10n.rxStartFailed,
    'rx_control_taken' => l10n.rxControlTaken,
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
    'error_pairing_invalid' => l10n.errorPairingInvalid,
    'error_pairing_expired' => l10n.errorPairingExpired,
    'error_pairing_used' => l10n.errorPairingUsed,
    'error_rate_limited' => l10n.errorRateLimited,
    'error_station_offline' => l10n.errorStationOffline,
    'error_audio_device_unavailable' => l10n.errorAudioDeviceUnavailable,
    'error_subscription_inactive' => l10n.errorSubscriptionInactive,
    'error_email_not_verified' => l10n.errorEmailNotVerified,
    'error_plan_unavailable' => l10n.errorPlanUnavailable,
    'error_history_locked' => l10n.errorHistoryLocked,
    'error_service_unavailable' => l10n.errorServiceUnavailable,
    'error_station_processing' => l10n.errorStationProcessing,
    'error_segment_failed' => l10n.errorSegmentFailed,
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
    _ => l10n.errorRequestFailed,
  };
}

String txStatusLabel(AppLocalizations l10n, String status) => switch (status) {
  'synthesizing' => l10n.txStatusSynthesizing,
  'queued' => l10n.txStatusQueued,
  'claimed' => l10n.txStatusClaimed,
  'transmitting' => l10n.txStatusTransmitting,
  'completed' => l10n.txStatusCompleted,
  'failed' => l10n.txStatusFailed,
  'processing' => l10n.txStatusProcessing,
  'review_ready' => l10n.txStatusReviewReady,
  'cancelled' => l10n.txStatusCancelled,
  _ => l10n.txStatusUnknown,
};
