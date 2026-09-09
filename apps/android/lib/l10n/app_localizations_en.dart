// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get steeringWheel => 'Simulated steering wheel';

  @override
  String get steeringLeft => 'Left';

  @override
  String get steeringRight => 'Right';

  @override
  String get steeringStraight => 'Straight';

  @override
  String get steeringCenter => 'Center';

  @override
  String get steeringAuto => 'Auto — simulation';

  @override
  String get moduleDevices => 'Devices';

  @override
  String get modulePending => 'Not integrated';

  @override
  String get stationUnavailable => 'Station unavailable';

  @override
  String get dashboard => 'Dashboard';

  @override
  String get speed => 'Speed';

  @override
  String get depth => 'Depth';

  @override
  String get heading => 'Heading';

  @override
  String get position => 'Position';

  @override
  String get map => 'Coordinate map';

  @override
  String get control => 'Control';

  @override
  String get auto => 'Auto';

  @override
  String get manual => 'Manual';

  @override
  String get dashboardStatus => 'Status';

  @override
  String get stationOnline => 'Station Online';

  @override
  String get stationOffline => 'Station Offline';

  @override
  String get telemetryMock => 'Simulated telemetry';

  @override
  String get controlMock => 'Simulation — no hardware connected';

  @override
  String get mapMockNotice => 'Simulation — not for navigation';

  @override
  String get telemetryMissing => 'Simulated telemetry — waiting for data';

  @override
  String get telemetryFresh => 'Simulated telemetry — updating';

  @override
  String get telemetryStale => 'Simulated telemetry — stale';

  @override
  String get telemetryError => 'Simulated telemetry — data error';

  @override
  String get start => 'Start';

  @override
  String get stop => 'Stop';

  @override
  String get starting => 'Starting…';

  @override
  String get stopping => 'Stopping…';

  @override
  String get waiting => 'Waiting for station';

  @override
  String get history => 'History';

  @override
  String get enableLiveAudio => 'Enable automatic audio playback';

  @override
  String get disableLiveAudio => 'Disable automatic audio playback';

  @override
  String get rxHeard => 'Heard';

  @override
  String get rxTranslateTo => 'Translate to';

  @override
  String get detecting => 'Detecting';

  @override
  String get translations => 'Live translations';

  @override
  String get emptyTitle => 'Waiting for speech';

  @override
  String get emptyBody =>
      'Start capture to receive transcript and translation.';

  @override
  String get retry => 'Retry';

  @override
  String get rxAudioInputNotFound =>
      'No USB SoundCard input was found. Connect the device and try again.';

  @override
  String get rxStartFailed => 'The Station could not start RX.';

  @override
  String get offline => 'Offline for more than 15 seconds';

  @override
  String get apiReady => 'API READY';

  @override
  String get apiError => 'API ERROR';

  @override
  String get quotaNear => 'You are nearing your plan usage limit.';

  @override
  String get quotaExhausted => 'Your plan usage limit has been reached.';

  @override
  String get settings => 'Settings';

  @override
  String get uiLanguage => 'Interface language';

  @override
  String get country => 'Country';

  @override
  String get countryNotSet => 'Not set';

  @override
  String get countrySearchHint => 'Search countries';

  @override
  String get selectCountry => 'Select country';

  @override
  String get selectTimezone => 'Select timezone';

  @override
  String get countryChangeNotice =>
      'New recordings are stored under this timezone\'s date.';

  @override
  String get stations => 'My stations';

  @override
  String get account => 'Account';

  @override
  String get pairStation => 'Pair station';

  @override
  String get noStation => 'No stations yet';

  @override
  String get noStationBody =>
      'Scan the device QR label or use a temporary pairing code.';

  @override
  String get signIn => 'Sign in';

  @override
  String get signUp => 'Sign up';

  @override
  String get signingIn => 'Working...';

  @override
  String get password => 'Password';

  @override
  String get confirmPassword => 'Confirm password';

  @override
  String get showPassword => 'Show password';

  @override
  String get hidePassword => 'Hide password';

  @override
  String get google => 'Continue with Google';

  @override
  String get googleSignUp => 'Sign up with Google';

  @override
  String get createAccount => 'Create account';

  @override
  String get authEmailRequired => 'Enter your email.';

  @override
  String get authInvalidEmail => 'Enter a valid email address.';

  @override
  String get authPasswordRequired => 'Enter your password.';

  @override
  String get authPasswordRequirements =>
      'Use at least 6 characters with an uppercase letter, a letter, and a number.';

  @override
  String get authConfirmRequired => 'Confirm your password.';

  @override
  String get authPasswordMismatch => 'The passwords do not match.';

  @override
  String get authInvalidCredentials => 'The email or password is incorrect.';

  @override
  String get authEmailInUse => 'This email is already in use.';

  @override
  String get authWeakPassword => 'The password is too weak.';

  @override
  String get authUserDisabled => 'This account has been disabled.';

  @override
  String get authTooManyRequests => 'Too many attempts. Try again later.';

  @override
  String get authNetworkError => 'Unable to connect. Check your network.';

  @override
  String get authGoogleError => 'Unable to sign in with Google.';

  @override
  String get authUnknownError => 'Authentication failed. Please try again.';

  @override
  String get verifyEmailTitle => 'Verify your email';

  @override
  String verifyEmailBody(Object email) {
    return 'We sent a verification link to $email. Open it before continuing.';
  }

  @override
  String get verificationCheck => 'I have verified';

  @override
  String get verificationStillPending => 'Your email is not verified yet.';

  @override
  String get verificationResent => 'A new verification email was sent.';

  @override
  String verificationResendWait(Object seconds) {
    return 'Resend in $seconds seconds';
  }

  @override
  String get confirmSignOut => 'Sign out?';

  @override
  String get confirmSignOutBody =>
      'Are you sure you want to sign out of PRANA ELEX?';

  @override
  String get tagline => 'Monitor and control your VHF stations.';

  @override
  String get accountPlan => 'Account and plan';

  @override
  String get signOut => 'Sign out';

  @override
  String get emailVerified => 'Email verified';

  @override
  String get emailUnverified => 'Email not verified';

  @override
  String get resendVerification => 'Resend verification email';

  @override
  String get deviceLabel => 'Device label';

  @override
  String get temporaryCode => 'Temporary code';

  @override
  String get scanQr => 'Open QR scanner';

  @override
  String get close => 'Close';

  @override
  String get loadStationError => 'Unable to load stations';

  @override
  String get noHistoryDays => 'No translation history yet';

  @override
  String get noHistoryDaysBody =>
      'Days containing translations will appear here.';

  @override
  String historyDayTitle(Object date) {
    return 'Date $date';
  }

  @override
  String historyDaySummary(Object count, Object range) {
    return '$count logs • $range';
  }

  @override
  String get syncing => 'Synchronizing';

  @override
  String get connectStation => 'Connect PRANA Station';

  @override
  String get labelHelp =>
      'Scan the fixed QR label attached to the Raspberry Pi or Laptop.';

  @override
  String get temporaryHelp =>
      'Use a temporary code created by a Laptop or legacy station.';

  @override
  String get activationHelp =>
      '16 characters, grouped automatically in blocks of four';

  @override
  String get stationMissing => 'Station no longer exists';

  @override
  String get realtimeError => 'Realtime connection lost';

  @override
  String get invalidPairingQr => 'This is not a PRANA ELEX pairing QR code.';

  @override
  String get invalidActivation =>
      'Enter a 10-character Setup ID and 16-character Activation Code.';

  @override
  String get invalidTemporaryPairing =>
      'Enter a Pairing ID and an 8-character temporary code.';

  @override
  String get stationSettings => 'Station settings';

  @override
  String get captureMode => 'Capture mode';

  @override
  String get audioDevice => 'Audio device';

  @override
  String get refreshDevices => 'Refresh devices';

  @override
  String get deviceScanChanged => 'The device list has been updated.';

  @override
  String get deviceScanUnchanged => 'Scan complete. No device changes found.';

  @override
  String get deviceScanTimeout =>
      'The Station did not return scan results. Check its connection.';

  @override
  String get audioSource => 'Audio source';

  @override
  String get txOutputDevice => 'Transmit device (TX)';

  @override
  String get txOutputVia => 'TX plays through';

  @override
  String get txStartRequiredShort => 'START FIRST';

  @override
  String get txTranslationEditHint =>
      'Edit the text that will be spoken before sending';

  @override
  String get stationInformation => 'Station information';

  @override
  String get stationCode => 'Station code';

  @override
  String get stationCodeHint =>
      'Send this code to the manufacturer when you need recordings extracted.';

  @override
  String get stationCodeCopied => 'Station code copied';

  @override
  String get copy => 'Copy';

  @override
  String get storagePath => 'Station storage path';

  @override
  String get activeCapture => 'Active capture configuration';

  @override
  String get lastDeviceScan => 'Last device scan';

  @override
  String get capabilitiesUnavailable =>
      'The Station has not reported audio capabilities.';

  @override
  String get save => 'Save changes';

  @override
  String get savingChanges => 'Saving…';

  @override
  String get applyingChanges => 'Applying…';

  @override
  String get settingsSyncDelayed =>
      'Changes were saved, but realtime data has not synchronized yet. The app will keep waiting to avoid a duplicate command.';

  @override
  String get historySearch => 'Search transcripts or translations';

  @override
  String get txHistoryEmpty => 'No TX history yet';

  @override
  String get txHistoryEmptyBody =>
      'Confirmed TX transmissions will appear here.';

  @override
  String get txHistoryEdited => 'Edited';

  @override
  String txHistoryAttempt(Object attempt) {
    return 'Attempt $attempt';
  }

  @override
  String get playAudio => 'Play audio';

  @override
  String get txStatusSynthesizing => 'Synthesizing';

  @override
  String get txStatusQueued => 'Queued';

  @override
  String get txStatusClaimed => 'Claimed';

  @override
  String get txStatusTransmitting => 'Transmitting';

  @override
  String get txStatusCompleted => 'Completed';

  @override
  String get txStatusFailed => 'Failed';

  @override
  String get forgotPassword => 'Forgot password';

  @override
  String get resetPassword => 'Send password reset email';

  @override
  String get resetPasswordShort => 'Reset password';

  @override
  String get resetSent =>
      'A password reset email was sent if the account exists.';

  @override
  String get linked => 'Linked';

  @override
  String get notLinked => 'Not linked';

  @override
  String get linkGoogle => 'Link Google';

  @override
  String get usage => 'Usage';

  @override
  String get plans => 'Plans';

  @override
  String get changePlan => 'Change plan';

  @override
  String get collapse => 'Collapse';

  @override
  String get seconds => 'seconds';

  @override
  String get devices => 'Devices and stations';

  @override
  String get confirmRevoke => 'Confirm revoke';

  @override
  String get revoke => 'Revoke';

  @override
  String get confirmRemoveStation => 'Remove Station?';

  @override
  String get removeStation => 'Remove Station';

  @override
  String removeStationBody(Object name) {
    return 'Remove $name from this account? The Station will stop and its QR label can be scanned by another account.';
  }

  @override
  String get errorStationNotPaired =>
      'The Station is not paired with an account. Scan its QR label.';

  @override
  String get errorStationRevoked =>
      'The Station is locked. An administrator must release it before it can be paired again.';

  @override
  String get errorStationLimitReached =>
      'This account has reached its Station limit for the current plan.';

  @override
  String get errorActivationInvalid =>
      'The Setup ID or Activation Code is invalid.';

  @override
  String get errorStationAlreadyClaimed =>
      'The Station already belongs to another account.';

  @override
  String get done => 'Completed';

  @override
  String historyRestricted(Object days) {
    return 'Recent results are limited by your plan. Full history unlocks after $days day(s).';
  }

  @override
  String get errorConnectionTimeout =>
      'Cannot connect to PRANA API. On a physical phone, make sure API_URL is not 10.0.2.2.';

  @override
  String get errorRequestTimeout =>
      'PRANA API took too long to respond. Try again.';

  @override
  String get errorApiUnreachable =>
      'PRANA API is unreachable. Check the network and server address.';

  @override
  String get errorRequestFailed =>
      'The request could not be completed. Try again.';

  @override
  String processingRetrying(Object attempt) {
    return 'The server is busy, retrying ($attempt/3)…';
  }

  @override
  String get speakTranslation => 'Speak translation';

  @override
  String get stopSpeaking => 'Stop speaking';

  @override
  String get ttsLanguageUnavailable =>
      'This phone has no voice for that language. Install Text-to-Speech data in Android settings.';

  @override
  String get ttsPlaybackError =>
      'Speech playback failed. Check the phone Text-to-Speech engine.';

  @override
  String get txTitle => 'Transmit a translation over VHF';

  @override
  String get txSubtitle =>
      'Hold PTT to speak, then review the translation before transmission.';

  @override
  String get txHoldToTalk => 'HOLD TO TALK';

  @override
  String get txReleaseToStop => 'RELEASE TO STOP';

  @override
  String get txTransmitIn => 'Transmit in';

  @override
  String get txReviewShort => 'REVIEW';

  @override
  String get txDoneShort => 'DONE';

  @override
  String get txProcessingShort => 'TRANSLATING';

  @override
  String get txQueuedShort => 'QUEUED';

  @override
  String get txTransmittingShort => 'TRANSMITTING';

  @override
  String get txRecording => 'Recording voice';

  @override
  String get txPttHint =>
      'Hold the button while speaking. Release it to create a translation.';

  @override
  String txMaxDuration(Object seconds) {
    return 'Maximum $seconds seconds per transmission.';
  }

  @override
  String get txProcessing => 'Preparing translation';

  @override
  String get txProcessingBody =>
      'PRANA is transcribing, translating, and preparing a sample voice.';

  @override
  String get txReviewTitle => 'Review before transmission';

  @override
  String get txTranscript => 'Recognized speech';

  @override
  String get txTranslation => 'Translation to transmit';

  @override
  String get txTransmit => 'Transmit over VHF';

  @override
  String get txCancel => 'Discard draft';

  @override
  String get txQueued => 'Waiting for Station';

  @override
  String get txQueuedBody =>
      'The translation is ready and waiting for its transmission turn.';

  @override
  String get txTransmitting => 'Station is transmitting';

  @override
  String get txTransmittingBody =>
      'RX is paused while the TX signal is being transmitted.';

  @override
  String get txCompleted => 'Transmission complete';

  @override
  String get txCompletedBody =>
      'The Station released PTT and returned to RX mode.';

  @override
  String get txNewMessage => 'Create another transmission';

  @override
  String get txStationOffline =>
      'The Station is offline. TX cannot be started.';

  @override
  String get txStationOfflineDuringTx =>
      'Connection to the Station was lost during transmission. The TX result is unconfirmed.';

  @override
  String get txPttUnavailable =>
      'PTT control is unavailable. Check the Station GPIO or configuration.';

  @override
  String get txRetryWaitingStation =>
      'Wait for the Station to reconnect and confirm failure before retrying.';

  @override
  String get txRecordingShort => 'RECORDING';

  @override
  String get txReleaseHint => 'Release to finish';

  @override
  String get txStationBusy => 'Another device is currently using this Station.';

  @override
  String get txChannelBusy =>
      'The VHF channel is busy. The transmission was cancelled.';

  @override
  String get txExpired => 'The TX session expired. Please record it again.';

  @override
  String get txProcessingFailed =>
      'The translation could not be prepared. Please try again.';

  @override
  String get txAudioTooLong =>
      'The recording exceeds the allowed duration. Please record it again.';

  @override
  String get txOutputTooLong =>
      'The translated audio exceeds 120 seconds. Shorten the text and try again.';

  @override
  String get txSynthesisTimeout =>
      'TX audio synthesis timed out. The job stopped safely; retry manually.';

  @override
  String get txPlaybackTimeout =>
      'TX playback timed out. PTT was released safely; check the Station.';

  @override
  String get txTransmissionFailed =>
      'The Station could not transmit the translation.';

  @override
  String get txDiscardTitle => 'Discard the current TX draft?';

  @override
  String get txDiscardBody =>
      'The untransmitted recording or translation will be deleted.';

  @override
  String get txDiscard => 'Discard and leave';

  @override
  String get countryLanguageUnavailable =>
      'Only an English interface is currently available for this country.';

  @override
  String get darkMode => 'Dark mode';

  @override
  String get darkModeHint => 'Use the dark appearance throughout the app';
}
