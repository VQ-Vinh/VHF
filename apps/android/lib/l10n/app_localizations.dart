import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';
import 'app_localizations_vi.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('vi'),
  ];

  /// No description provided for @steeringWheel.
  ///
  /// In en, this message translates to:
  /// **'Simulated steering wheel'**
  String get steeringWheel;

  /// No description provided for @steeringLeft.
  ///
  /// In en, this message translates to:
  /// **'Left'**
  String get steeringLeft;

  /// No description provided for @steeringRight.
  ///
  /// In en, this message translates to:
  /// **'Right'**
  String get steeringRight;

  /// No description provided for @steeringStraight.
  ///
  /// In en, this message translates to:
  /// **'Straight'**
  String get steeringStraight;

  /// No description provided for @steeringCenter.
  ///
  /// In en, this message translates to:
  /// **'Center'**
  String get steeringCenter;

  /// No description provided for @steeringAuto.
  ///
  /// In en, this message translates to:
  /// **'Auto — simulation'**
  String get steeringAuto;

  /// No description provided for @moduleDevices.
  ///
  /// In en, this message translates to:
  /// **'Devices'**
  String get moduleDevices;

  /// No description provided for @modulePending.
  ///
  /// In en, this message translates to:
  /// **'Not integrated'**
  String get modulePending;

  /// No description provided for @stationUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Station unavailable'**
  String get stationUnavailable;

  /// No description provided for @dashboard.
  ///
  /// In en, this message translates to:
  /// **'Dashboard'**
  String get dashboard;

  /// No description provided for @speed.
  ///
  /// In en, this message translates to:
  /// **'Speed'**
  String get speed;

  /// No description provided for @depth.
  ///
  /// In en, this message translates to:
  /// **'Depth'**
  String get depth;

  /// No description provided for @heading.
  ///
  /// In en, this message translates to:
  /// **'Heading'**
  String get heading;

  /// No description provided for @position.
  ///
  /// In en, this message translates to:
  /// **'Position'**
  String get position;

  /// No description provided for @map.
  ///
  /// In en, this message translates to:
  /// **'Coordinate map'**
  String get map;

  /// No description provided for @control.
  ///
  /// In en, this message translates to:
  /// **'Control'**
  String get control;

  /// No description provided for @auto.
  ///
  /// In en, this message translates to:
  /// **'Auto'**
  String get auto;

  /// No description provided for @manual.
  ///
  /// In en, this message translates to:
  /// **'Manual'**
  String get manual;

  /// No description provided for @dashboardStatus.
  ///
  /// In en, this message translates to:
  /// **'Status'**
  String get dashboardStatus;

  /// No description provided for @stationOnline.
  ///
  /// In en, this message translates to:
  /// **'Station Online'**
  String get stationOnline;

  /// No description provided for @stationOffline.
  ///
  /// In en, this message translates to:
  /// **'Station Offline'**
  String get stationOffline;

  /// No description provided for @telemetryMock.
  ///
  /// In en, this message translates to:
  /// **'Simulated telemetry'**
  String get telemetryMock;

  /// No description provided for @controlMock.
  ///
  /// In en, this message translates to:
  /// **'Simulation — no hardware connected'**
  String get controlMock;

  /// No description provided for @mapMockNotice.
  ///
  /// In en, this message translates to:
  /// **'Simulation — not for navigation'**
  String get mapMockNotice;

  /// No description provided for @telemetryMissing.
  ///
  /// In en, this message translates to:
  /// **'Simulated telemetry — waiting for data'**
  String get telemetryMissing;

  /// No description provided for @telemetryFresh.
  ///
  /// In en, this message translates to:
  /// **'Simulated telemetry — updating'**
  String get telemetryFresh;

  /// No description provided for @telemetryStale.
  ///
  /// In en, this message translates to:
  /// **'Simulated telemetry — stale'**
  String get telemetryStale;

  /// No description provided for @telemetryError.
  ///
  /// In en, this message translates to:
  /// **'Simulated telemetry — data error'**
  String get telemetryError;

  /// No description provided for @start.
  ///
  /// In en, this message translates to:
  /// **'Start'**
  String get start;

  /// No description provided for @stop.
  ///
  /// In en, this message translates to:
  /// **'Stop'**
  String get stop;

  /// No description provided for @starting.
  ///
  /// In en, this message translates to:
  /// **'Starting…'**
  String get starting;

  /// No description provided for @stopping.
  ///
  /// In en, this message translates to:
  /// **'Stopping…'**
  String get stopping;

  /// No description provided for @waiting.
  ///
  /// In en, this message translates to:
  /// **'Waiting for station'**
  String get waiting;

  /// No description provided for @history.
  ///
  /// In en, this message translates to:
  /// **'History'**
  String get history;

  /// No description provided for @enableLiveAudio.
  ///
  /// In en, this message translates to:
  /// **'Enable automatic audio playback'**
  String get enableLiveAudio;

  /// No description provided for @disableLiveAudio.
  ///
  /// In en, this message translates to:
  /// **'Disable automatic audio playback'**
  String get disableLiveAudio;

  /// No description provided for @rxHeard.
  ///
  /// In en, this message translates to:
  /// **'Heard'**
  String get rxHeard;

  /// No description provided for @rxTranslateTo.
  ///
  /// In en, this message translates to:
  /// **'Translate to'**
  String get rxTranslateTo;

  /// No description provided for @detecting.
  ///
  /// In en, this message translates to:
  /// **'Detecting'**
  String get detecting;

  /// No description provided for @translations.
  ///
  /// In en, this message translates to:
  /// **'Live translations'**
  String get translations;

  /// No description provided for @emptyTitle.
  ///
  /// In en, this message translates to:
  /// **'Waiting for speech'**
  String get emptyTitle;

  /// No description provided for @emptyBody.
  ///
  /// In en, this message translates to:
  /// **'Start capture to receive transcript and translation.'**
  String get emptyBody;

  /// No description provided for @retry.
  ///
  /// In en, this message translates to:
  /// **'Retry'**
  String get retry;

  /// No description provided for @rxAudioInputNotFound.
  ///
  /// In en, this message translates to:
  /// **'No USB SoundCard input was found. Connect the device and try again.'**
  String get rxAudioInputNotFound;

  /// No description provided for @rxStartFailed.
  ///
  /// In en, this message translates to:
  /// **'The Station could not start RX.'**
  String get rxStartFailed;

  /// No description provided for @offline.
  ///
  /// In en, this message translates to:
  /// **'Offline for more than 15 seconds'**
  String get offline;

  /// No description provided for @apiReady.
  ///
  /// In en, this message translates to:
  /// **'API READY'**
  String get apiReady;

  /// No description provided for @apiError.
  ///
  /// In en, this message translates to:
  /// **'API ERROR'**
  String get apiError;

  /// No description provided for @quotaNear.
  ///
  /// In en, this message translates to:
  /// **'You are nearing your plan usage limit.'**
  String get quotaNear;

  /// No description provided for @quotaExhausted.
  ///
  /// In en, this message translates to:
  /// **'Your plan usage limit has been reached.'**
  String get quotaExhausted;

  /// No description provided for @settings.
  ///
  /// In en, this message translates to:
  /// **'Settings'**
  String get settings;

  /// No description provided for @uiLanguage.
  ///
  /// In en, this message translates to:
  /// **'Interface language'**
  String get uiLanguage;

  /// No description provided for @country.
  ///
  /// In en, this message translates to:
  /// **'Country'**
  String get country;

  /// No description provided for @countryNotSet.
  ///
  /// In en, this message translates to:
  /// **'Not set'**
  String get countryNotSet;

  /// No description provided for @countrySearchHint.
  ///
  /// In en, this message translates to:
  /// **'Search countries'**
  String get countrySearchHint;

  /// No description provided for @selectCountry.
  ///
  /// In en, this message translates to:
  /// **'Select country'**
  String get selectCountry;

  /// No description provided for @selectTimezone.
  ///
  /// In en, this message translates to:
  /// **'Select timezone'**
  String get selectTimezone;

  /// No description provided for @countryChangeNotice.
  ///
  /// In en, this message translates to:
  /// **'New recordings are stored under this timezone\'s date.'**
  String get countryChangeNotice;

  /// No description provided for @stations.
  ///
  /// In en, this message translates to:
  /// **'My stations'**
  String get stations;

  /// No description provided for @account.
  ///
  /// In en, this message translates to:
  /// **'Account'**
  String get account;

  /// No description provided for @pairStation.
  ///
  /// In en, this message translates to:
  /// **'Pair station'**
  String get pairStation;

  /// No description provided for @noStation.
  ///
  /// In en, this message translates to:
  /// **'No stations yet'**
  String get noStation;

  /// No description provided for @noStationBody.
  ///
  /// In en, this message translates to:
  /// **'Scan the device QR label or use a temporary pairing code.'**
  String get noStationBody;

  /// No description provided for @signIn.
  ///
  /// In en, this message translates to:
  /// **'Sign in'**
  String get signIn;

  /// No description provided for @signUp.
  ///
  /// In en, this message translates to:
  /// **'Sign up'**
  String get signUp;

  /// No description provided for @signingIn.
  ///
  /// In en, this message translates to:
  /// **'Working...'**
  String get signingIn;

  /// No description provided for @password.
  ///
  /// In en, this message translates to:
  /// **'Password'**
  String get password;

  /// No description provided for @confirmPassword.
  ///
  /// In en, this message translates to:
  /// **'Confirm password'**
  String get confirmPassword;

  /// No description provided for @showPassword.
  ///
  /// In en, this message translates to:
  /// **'Show password'**
  String get showPassword;

  /// No description provided for @hidePassword.
  ///
  /// In en, this message translates to:
  /// **'Hide password'**
  String get hidePassword;

  /// No description provided for @google.
  ///
  /// In en, this message translates to:
  /// **'Continue with Google'**
  String get google;

  /// No description provided for @googleSignUp.
  ///
  /// In en, this message translates to:
  /// **'Sign up with Google'**
  String get googleSignUp;

  /// No description provided for @createAccount.
  ///
  /// In en, this message translates to:
  /// **'Create account'**
  String get createAccount;

  /// No description provided for @authEmailRequired.
  ///
  /// In en, this message translates to:
  /// **'Enter your email.'**
  String get authEmailRequired;

  /// No description provided for @authInvalidEmail.
  ///
  /// In en, this message translates to:
  /// **'Enter a valid email address.'**
  String get authInvalidEmail;

  /// No description provided for @authPasswordRequired.
  ///
  /// In en, this message translates to:
  /// **'Enter your password.'**
  String get authPasswordRequired;

  /// No description provided for @authPasswordRequirements.
  ///
  /// In en, this message translates to:
  /// **'Use at least 6 characters with an uppercase letter, a letter, and a number.'**
  String get authPasswordRequirements;

  /// No description provided for @authConfirmRequired.
  ///
  /// In en, this message translates to:
  /// **'Confirm your password.'**
  String get authConfirmRequired;

  /// No description provided for @authPasswordMismatch.
  ///
  /// In en, this message translates to:
  /// **'The passwords do not match.'**
  String get authPasswordMismatch;

  /// No description provided for @authInvalidCredentials.
  ///
  /// In en, this message translates to:
  /// **'The email or password is incorrect.'**
  String get authInvalidCredentials;

  /// No description provided for @authEmailInUse.
  ///
  /// In en, this message translates to:
  /// **'This email is already in use.'**
  String get authEmailInUse;

  /// No description provided for @authWeakPassword.
  ///
  /// In en, this message translates to:
  /// **'The password is too weak.'**
  String get authWeakPassword;

  /// No description provided for @authUserDisabled.
  ///
  /// In en, this message translates to:
  /// **'This account has been disabled.'**
  String get authUserDisabled;

  /// No description provided for @authTooManyRequests.
  ///
  /// In en, this message translates to:
  /// **'Too many attempts. Try again later.'**
  String get authTooManyRequests;

  /// No description provided for @authNetworkError.
  ///
  /// In en, this message translates to:
  /// **'Unable to connect. Check your network.'**
  String get authNetworkError;

  /// No description provided for @authGoogleError.
  ///
  /// In en, this message translates to:
  /// **'Unable to sign in with Google.'**
  String get authGoogleError;

  /// No description provided for @authUnknownError.
  ///
  /// In en, this message translates to:
  /// **'Authentication failed. Please try again.'**
  String get authUnknownError;

  /// No description provided for @verifyEmailTitle.
  ///
  /// In en, this message translates to:
  /// **'Verify your email'**
  String get verifyEmailTitle;

  /// No description provided for @verifyEmailBody.
  ///
  /// In en, this message translates to:
  /// **'We sent a verification link to {email}. Open it before continuing.'**
  String verifyEmailBody(Object email);

  /// No description provided for @verificationCheck.
  ///
  /// In en, this message translates to:
  /// **'I have verified'**
  String get verificationCheck;

  /// No description provided for @verificationStillPending.
  ///
  /// In en, this message translates to:
  /// **'Your email is not verified yet.'**
  String get verificationStillPending;

  /// No description provided for @verificationResent.
  ///
  /// In en, this message translates to:
  /// **'A new verification email was sent.'**
  String get verificationResent;

  /// No description provided for @verificationResendWait.
  ///
  /// In en, this message translates to:
  /// **'Resend in {seconds} seconds'**
  String verificationResendWait(Object seconds);

  /// No description provided for @confirmSignOut.
  ///
  /// In en, this message translates to:
  /// **'Sign out?'**
  String get confirmSignOut;

  /// No description provided for @confirmSignOutBody.
  ///
  /// In en, this message translates to:
  /// **'Are you sure you want to sign out of PRANA ELEX?'**
  String get confirmSignOutBody;

  /// No description provided for @tagline.
  ///
  /// In en, this message translates to:
  /// **'Monitor and control your VHF stations.'**
  String get tagline;

  /// No description provided for @accountPlan.
  ///
  /// In en, this message translates to:
  /// **'Account and plan'**
  String get accountPlan;

  /// No description provided for @signOut.
  ///
  /// In en, this message translates to:
  /// **'Sign out'**
  String get signOut;

  /// No description provided for @emailVerified.
  ///
  /// In en, this message translates to:
  /// **'Email verified'**
  String get emailVerified;

  /// No description provided for @emailUnverified.
  ///
  /// In en, this message translates to:
  /// **'Email not verified'**
  String get emailUnverified;

  /// No description provided for @resendVerification.
  ///
  /// In en, this message translates to:
  /// **'Resend verification email'**
  String get resendVerification;

  /// No description provided for @deviceLabel.
  ///
  /// In en, this message translates to:
  /// **'Device label'**
  String get deviceLabel;

  /// No description provided for @temporaryCode.
  ///
  /// In en, this message translates to:
  /// **'Temporary code'**
  String get temporaryCode;

  /// No description provided for @scanQr.
  ///
  /// In en, this message translates to:
  /// **'Open QR scanner'**
  String get scanQr;

  /// No description provided for @close.
  ///
  /// In en, this message translates to:
  /// **'Close'**
  String get close;

  /// No description provided for @loadStationError.
  ///
  /// In en, this message translates to:
  /// **'Unable to load stations'**
  String get loadStationError;

  /// No description provided for @noHistoryDays.
  ///
  /// In en, this message translates to:
  /// **'No translation history yet'**
  String get noHistoryDays;

  /// No description provided for @noHistoryDaysBody.
  ///
  /// In en, this message translates to:
  /// **'Days containing translations will appear here.'**
  String get noHistoryDaysBody;

  /// No description provided for @historyDayTitle.
  ///
  /// In en, this message translates to:
  /// **'Date {date}'**
  String historyDayTitle(Object date);

  /// No description provided for @historyDaySummary.
  ///
  /// In en, this message translates to:
  /// **'{count} logs • {range}'**
  String historyDaySummary(Object count, Object range);

  /// No description provided for @syncing.
  ///
  /// In en, this message translates to:
  /// **'Synchronizing'**
  String get syncing;

  /// No description provided for @connectStation.
  ///
  /// In en, this message translates to:
  /// **'Connect PRANA Station'**
  String get connectStation;

  /// No description provided for @labelHelp.
  ///
  /// In en, this message translates to:
  /// **'Scan the fixed QR label attached to the Raspberry Pi or Laptop.'**
  String get labelHelp;

  /// No description provided for @temporaryHelp.
  ///
  /// In en, this message translates to:
  /// **'Use a temporary code created by a Laptop or legacy station.'**
  String get temporaryHelp;

  /// No description provided for @activationHelp.
  ///
  /// In en, this message translates to:
  /// **'16 characters, grouped automatically in blocks of four'**
  String get activationHelp;

  /// No description provided for @stationMissing.
  ///
  /// In en, this message translates to:
  /// **'Station no longer exists'**
  String get stationMissing;

  /// No description provided for @realtimeError.
  ///
  /// In en, this message translates to:
  /// **'Realtime connection lost'**
  String get realtimeError;

  /// No description provided for @invalidPairingQr.
  ///
  /// In en, this message translates to:
  /// **'This is not a PRANA ELEX pairing QR code.'**
  String get invalidPairingQr;

  /// No description provided for @invalidActivation.
  ///
  /// In en, this message translates to:
  /// **'Enter a 10-character Setup ID and 16-character Activation Code.'**
  String get invalidActivation;

  /// No description provided for @invalidTemporaryPairing.
  ///
  /// In en, this message translates to:
  /// **'Enter a Pairing ID and an 8-character temporary code.'**
  String get invalidTemporaryPairing;

  /// No description provided for @stationSettings.
  ///
  /// In en, this message translates to:
  /// **'Station settings'**
  String get stationSettings;

  /// No description provided for @captureMode.
  ///
  /// In en, this message translates to:
  /// **'Capture mode'**
  String get captureMode;

  /// No description provided for @audioDevice.
  ///
  /// In en, this message translates to:
  /// **'Audio device'**
  String get audioDevice;

  /// No description provided for @refreshDevices.
  ///
  /// In en, this message translates to:
  /// **'Refresh devices'**
  String get refreshDevices;

  /// No description provided for @deviceScanChanged.
  ///
  /// In en, this message translates to:
  /// **'The device list has been updated.'**
  String get deviceScanChanged;

  /// No description provided for @deviceScanUnchanged.
  ///
  /// In en, this message translates to:
  /// **'Scan complete. No device changes found.'**
  String get deviceScanUnchanged;

  /// No description provided for @deviceScanTimeout.
  ///
  /// In en, this message translates to:
  /// **'The Station did not return scan results. Check its connection.'**
  String get deviceScanTimeout;

  /// No description provided for @audioSource.
  ///
  /// In en, this message translates to:
  /// **'Audio source'**
  String get audioSource;

  /// No description provided for @txOutputDevice.
  ///
  /// In en, this message translates to:
  /// **'Transmit device (TX)'**
  String get txOutputDevice;

  /// No description provided for @txOutputVia.
  ///
  /// In en, this message translates to:
  /// **'TX plays through'**
  String get txOutputVia;

  /// No description provided for @txStartRequiredShort.
  ///
  /// In en, this message translates to:
  /// **'START FIRST'**
  String get txStartRequiredShort;

  /// No description provided for @txTranslationEditHint.
  ///
  /// In en, this message translates to:
  /// **'Edit the text that will be spoken before sending'**
  String get txTranslationEditHint;

  /// No description provided for @stationInformation.
  ///
  /// In en, this message translates to:
  /// **'Station information'**
  String get stationInformation;

  /// No description provided for @stationCode.
  ///
  /// In en, this message translates to:
  /// **'Station code'**
  String get stationCode;

  /// No description provided for @stationCodeHint.
  ///
  /// In en, this message translates to:
  /// **'Send this code to the manufacturer when you need recordings extracted.'**
  String get stationCodeHint;

  /// No description provided for @stationCodeCopied.
  ///
  /// In en, this message translates to:
  /// **'Station code copied'**
  String get stationCodeCopied;

  /// No description provided for @copy.
  ///
  /// In en, this message translates to:
  /// **'Copy'**
  String get copy;

  /// No description provided for @storagePath.
  ///
  /// In en, this message translates to:
  /// **'Station storage path'**
  String get storagePath;

  /// No description provided for @activeCapture.
  ///
  /// In en, this message translates to:
  /// **'Active capture configuration'**
  String get activeCapture;

  /// No description provided for @lastDeviceScan.
  ///
  /// In en, this message translates to:
  /// **'Last device scan'**
  String get lastDeviceScan;

  /// No description provided for @capabilitiesUnavailable.
  ///
  /// In en, this message translates to:
  /// **'The Station has not reported audio capabilities.'**
  String get capabilitiesUnavailable;

  /// No description provided for @save.
  ///
  /// In en, this message translates to:
  /// **'Save changes'**
  String get save;

  /// No description provided for @savingChanges.
  ///
  /// In en, this message translates to:
  /// **'Saving…'**
  String get savingChanges;

  /// No description provided for @applyingChanges.
  ///
  /// In en, this message translates to:
  /// **'Applying…'**
  String get applyingChanges;

  /// No description provided for @settingsSyncDelayed.
  ///
  /// In en, this message translates to:
  /// **'Changes were saved, but realtime data has not synchronized yet. The app will keep waiting to avoid a duplicate command.'**
  String get settingsSyncDelayed;

  /// No description provided for @historySearch.
  ///
  /// In en, this message translates to:
  /// **'Search transcripts or translations'**
  String get historySearch;

  /// No description provided for @txHistoryEmpty.
  ///
  /// In en, this message translates to:
  /// **'No TX history yet'**
  String get txHistoryEmpty;

  /// No description provided for @txHistoryEmptyBody.
  ///
  /// In en, this message translates to:
  /// **'Confirmed TX transmissions will appear here.'**
  String get txHistoryEmptyBody;

  /// No description provided for @txHistoryEdited.
  ///
  /// In en, this message translates to:
  /// **'Edited'**
  String get txHistoryEdited;

  /// No description provided for @txHistoryAttempt.
  ///
  /// In en, this message translates to:
  /// **'Attempt {attempt}'**
  String txHistoryAttempt(Object attempt);

  /// No description provided for @playAudio.
  ///
  /// In en, this message translates to:
  /// **'Play audio'**
  String get playAudio;

  /// No description provided for @txStatusSynthesizing.
  ///
  /// In en, this message translates to:
  /// **'Synthesizing'**
  String get txStatusSynthesizing;

  /// No description provided for @txStatusQueued.
  ///
  /// In en, this message translates to:
  /// **'Queued'**
  String get txStatusQueued;

  /// No description provided for @txStatusClaimed.
  ///
  /// In en, this message translates to:
  /// **'Claimed'**
  String get txStatusClaimed;

  /// No description provided for @txStatusTransmitting.
  ///
  /// In en, this message translates to:
  /// **'Transmitting'**
  String get txStatusTransmitting;

  /// No description provided for @txStatusCompleted.
  ///
  /// In en, this message translates to:
  /// **'Completed'**
  String get txStatusCompleted;

  /// No description provided for @txStatusFailed.
  ///
  /// In en, this message translates to:
  /// **'Failed'**
  String get txStatusFailed;

  /// No description provided for @forgotPassword.
  ///
  /// In en, this message translates to:
  /// **'Forgot password'**
  String get forgotPassword;

  /// No description provided for @resetPassword.
  ///
  /// In en, this message translates to:
  /// **'Send password reset email'**
  String get resetPassword;

  /// No description provided for @resetPasswordShort.
  ///
  /// In en, this message translates to:
  /// **'Reset password'**
  String get resetPasswordShort;

  /// No description provided for @resetSent.
  ///
  /// In en, this message translates to:
  /// **'A password reset email was sent if the account exists.'**
  String get resetSent;

  /// No description provided for @linked.
  ///
  /// In en, this message translates to:
  /// **'Linked'**
  String get linked;

  /// No description provided for @notLinked.
  ///
  /// In en, this message translates to:
  /// **'Not linked'**
  String get notLinked;

  /// No description provided for @linkGoogle.
  ///
  /// In en, this message translates to:
  /// **'Link Google'**
  String get linkGoogle;

  /// No description provided for @usage.
  ///
  /// In en, this message translates to:
  /// **'Usage'**
  String get usage;

  /// No description provided for @plans.
  ///
  /// In en, this message translates to:
  /// **'Plans'**
  String get plans;

  /// No description provided for @changePlan.
  ///
  /// In en, this message translates to:
  /// **'Change plan'**
  String get changePlan;

  /// No description provided for @collapse.
  ///
  /// In en, this message translates to:
  /// **'Collapse'**
  String get collapse;

  /// No description provided for @seconds.
  ///
  /// In en, this message translates to:
  /// **'seconds'**
  String get seconds;

  /// No description provided for @devices.
  ///
  /// In en, this message translates to:
  /// **'Devices and stations'**
  String get devices;

  /// No description provided for @confirmRevoke.
  ///
  /// In en, this message translates to:
  /// **'Confirm revoke'**
  String get confirmRevoke;

  /// No description provided for @revoke.
  ///
  /// In en, this message translates to:
  /// **'Revoke'**
  String get revoke;

  /// No description provided for @confirmRemoveStation.
  ///
  /// In en, this message translates to:
  /// **'Remove Station?'**
  String get confirmRemoveStation;

  /// No description provided for @removeStation.
  ///
  /// In en, this message translates to:
  /// **'Remove Station'**
  String get removeStation;

  /// No description provided for @removeStationBody.
  ///
  /// In en, this message translates to:
  /// **'Remove {name} from this account? The Station will stop and its QR label can be scanned by another account.'**
  String removeStationBody(Object name);

  /// No description provided for @errorStationNotPaired.
  ///
  /// In en, this message translates to:
  /// **'The Station is not paired with an account. Scan its QR label.'**
  String get errorStationNotPaired;

  /// No description provided for @errorStationRevoked.
  ///
  /// In en, this message translates to:
  /// **'The Station is locked. An administrator must release it before it can be paired again.'**
  String get errorStationRevoked;

  /// No description provided for @errorStationLimitReached.
  ///
  /// In en, this message translates to:
  /// **'This account has reached its Station limit for the current plan.'**
  String get errorStationLimitReached;

  /// No description provided for @errorActivationInvalid.
  ///
  /// In en, this message translates to:
  /// **'The Setup ID or Activation Code is invalid.'**
  String get errorActivationInvalid;

  /// No description provided for @errorStationAlreadyClaimed.
  ///
  /// In en, this message translates to:
  /// **'The Station already belongs to another account.'**
  String get errorStationAlreadyClaimed;

  /// No description provided for @done.
  ///
  /// In en, this message translates to:
  /// **'Completed'**
  String get done;

  /// No description provided for @historyRestricted.
  ///
  /// In en, this message translates to:
  /// **'Recent results are limited by your plan. Full history unlocks after {days} day(s).'**
  String historyRestricted(Object days);

  /// No description provided for @errorConnectionTimeout.
  ///
  /// In en, this message translates to:
  /// **'Cannot connect to PRANA API. On a physical phone, make sure API_URL is not 10.0.2.2.'**
  String get errorConnectionTimeout;

  /// No description provided for @errorRequestTimeout.
  ///
  /// In en, this message translates to:
  /// **'PRANA API took too long to respond. Try again.'**
  String get errorRequestTimeout;

  /// No description provided for @errorApiUnreachable.
  ///
  /// In en, this message translates to:
  /// **'PRANA API is unreachable. Check the network and server address.'**
  String get errorApiUnreachable;

  /// No description provided for @errorRequestFailed.
  ///
  /// In en, this message translates to:
  /// **'The request could not be completed. Try again.'**
  String get errorRequestFailed;

  /// No description provided for @processingRetrying.
  ///
  /// In en, this message translates to:
  /// **'The server is busy, retrying ({attempt}/3)…'**
  String processingRetrying(Object attempt);

  /// No description provided for @speakTranslation.
  ///
  /// In en, this message translates to:
  /// **'Speak translation'**
  String get speakTranslation;

  /// No description provided for @stopSpeaking.
  ///
  /// In en, this message translates to:
  /// **'Stop speaking'**
  String get stopSpeaking;

  /// No description provided for @ttsLanguageUnavailable.
  ///
  /// In en, this message translates to:
  /// **'This phone has no voice for that language. Install Text-to-Speech data in Android settings.'**
  String get ttsLanguageUnavailable;

  /// No description provided for @ttsPlaybackError.
  ///
  /// In en, this message translates to:
  /// **'Speech playback failed. Check the phone Text-to-Speech engine.'**
  String get ttsPlaybackError;

  /// No description provided for @txTitle.
  ///
  /// In en, this message translates to:
  /// **'Transmit a translation over VHF'**
  String get txTitle;

  /// No description provided for @txSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Hold PTT to speak, then review the translation before transmission.'**
  String get txSubtitle;

  /// No description provided for @txHoldToTalk.
  ///
  /// In en, this message translates to:
  /// **'HOLD TO TALK'**
  String get txHoldToTalk;

  /// No description provided for @txReleaseToStop.
  ///
  /// In en, this message translates to:
  /// **'RELEASE TO STOP'**
  String get txReleaseToStop;

  /// No description provided for @txTransmitIn.
  ///
  /// In en, this message translates to:
  /// **'Transmit in'**
  String get txTransmitIn;

  /// No description provided for @txReviewShort.
  ///
  /// In en, this message translates to:
  /// **'REVIEW'**
  String get txReviewShort;

  /// No description provided for @txDoneShort.
  ///
  /// In en, this message translates to:
  /// **'DONE'**
  String get txDoneShort;

  /// No description provided for @txProcessingShort.
  ///
  /// In en, this message translates to:
  /// **'TRANSLATING'**
  String get txProcessingShort;

  /// No description provided for @txQueuedShort.
  ///
  /// In en, this message translates to:
  /// **'QUEUED'**
  String get txQueuedShort;

  /// No description provided for @txTransmittingShort.
  ///
  /// In en, this message translates to:
  /// **'TRANSMITTING'**
  String get txTransmittingShort;

  /// No description provided for @txRecording.
  ///
  /// In en, this message translates to:
  /// **'Recording voice'**
  String get txRecording;

  /// No description provided for @txPttHint.
  ///
  /// In en, this message translates to:
  /// **'Hold the button while speaking. Release it to create a translation.'**
  String get txPttHint;

  /// No description provided for @txMaxDuration.
  ///
  /// In en, this message translates to:
  /// **'Maximum {seconds} seconds per transmission.'**
  String txMaxDuration(Object seconds);

  /// No description provided for @txProcessing.
  ///
  /// In en, this message translates to:
  /// **'Preparing translation'**
  String get txProcessing;

  /// No description provided for @txProcessingBody.
  ///
  /// In en, this message translates to:
  /// **'PRANA is transcribing, translating, and preparing a sample voice.'**
  String get txProcessingBody;

  /// No description provided for @txReviewTitle.
  ///
  /// In en, this message translates to:
  /// **'Review before transmission'**
  String get txReviewTitle;

  /// No description provided for @txTranscript.
  ///
  /// In en, this message translates to:
  /// **'Recognized speech'**
  String get txTranscript;

  /// No description provided for @txTranslation.
  ///
  /// In en, this message translates to:
  /// **'Translation to transmit'**
  String get txTranslation;

  /// No description provided for @txTransmit.
  ///
  /// In en, this message translates to:
  /// **'Transmit over VHF'**
  String get txTransmit;

  /// No description provided for @txCancel.
  ///
  /// In en, this message translates to:
  /// **'Discard draft'**
  String get txCancel;

  /// No description provided for @txQueued.
  ///
  /// In en, this message translates to:
  /// **'Waiting for Station'**
  String get txQueued;

  /// No description provided for @txQueuedBody.
  ///
  /// In en, this message translates to:
  /// **'The translation is ready and waiting for its transmission turn.'**
  String get txQueuedBody;

  /// No description provided for @txTransmitting.
  ///
  /// In en, this message translates to:
  /// **'Station is transmitting'**
  String get txTransmitting;

  /// No description provided for @txTransmittingBody.
  ///
  /// In en, this message translates to:
  /// **'RX is paused while the TX signal is being transmitted.'**
  String get txTransmittingBody;

  /// No description provided for @txCompleted.
  ///
  /// In en, this message translates to:
  /// **'Transmission complete'**
  String get txCompleted;

  /// No description provided for @txCompletedBody.
  ///
  /// In en, this message translates to:
  /// **'The Station released PTT and returned to RX mode.'**
  String get txCompletedBody;

  /// No description provided for @txNewMessage.
  ///
  /// In en, this message translates to:
  /// **'Create another transmission'**
  String get txNewMessage;

  /// No description provided for @txStationOffline.
  ///
  /// In en, this message translates to:
  /// **'The Station is offline. TX cannot be started.'**
  String get txStationOffline;

  /// No description provided for @txStationOfflineDuringTx.
  ///
  /// In en, this message translates to:
  /// **'Connection to the Station was lost during transmission. The TX result is unconfirmed.'**
  String get txStationOfflineDuringTx;

  /// No description provided for @txPttUnavailable.
  ///
  /// In en, this message translates to:
  /// **'PTT control is unavailable. Check the Station GPIO or configuration.'**
  String get txPttUnavailable;

  /// No description provided for @txRetryWaitingStation.
  ///
  /// In en, this message translates to:
  /// **'Wait for the Station to reconnect and confirm failure before retrying.'**
  String get txRetryWaitingStation;

  /// No description provided for @txRecordingShort.
  ///
  /// In en, this message translates to:
  /// **'RECORDING'**
  String get txRecordingShort;

  /// No description provided for @txReleaseHint.
  ///
  /// In en, this message translates to:
  /// **'Release to finish'**
  String get txReleaseHint;

  /// No description provided for @txStationBusy.
  ///
  /// In en, this message translates to:
  /// **'Another device is currently using this Station.'**
  String get txStationBusy;

  /// No description provided for @txChannelBusy.
  ///
  /// In en, this message translates to:
  /// **'The VHF channel is busy. The transmission was cancelled.'**
  String get txChannelBusy;

  /// No description provided for @txExpired.
  ///
  /// In en, this message translates to:
  /// **'The TX session expired. Please record it again.'**
  String get txExpired;

  /// No description provided for @txProcessingFailed.
  ///
  /// In en, this message translates to:
  /// **'The translation could not be prepared. Please try again.'**
  String get txProcessingFailed;

  /// No description provided for @txAudioTooLong.
  ///
  /// In en, this message translates to:
  /// **'The recording exceeds the allowed duration. Please record it again.'**
  String get txAudioTooLong;

  /// No description provided for @txOutputTooLong.
  ///
  /// In en, this message translates to:
  /// **'The translated audio exceeds 120 seconds. Shorten the text and try again.'**
  String get txOutputTooLong;

  /// No description provided for @txSynthesisTimeout.
  ///
  /// In en, this message translates to:
  /// **'TX audio synthesis timed out. The job stopped safely; retry manually.'**
  String get txSynthesisTimeout;

  /// No description provided for @txPlaybackTimeout.
  ///
  /// In en, this message translates to:
  /// **'TX playback timed out. PTT was released safely; check the Station.'**
  String get txPlaybackTimeout;

  /// No description provided for @txTransmissionFailed.
  ///
  /// In en, this message translates to:
  /// **'The Station could not transmit the translation.'**
  String get txTransmissionFailed;

  /// No description provided for @txDiscardTitle.
  ///
  /// In en, this message translates to:
  /// **'Discard the current TX draft?'**
  String get txDiscardTitle;

  /// No description provided for @txDiscardBody.
  ///
  /// In en, this message translates to:
  /// **'The untransmitted recording or translation will be deleted.'**
  String get txDiscardBody;

  /// No description provided for @txDiscard.
  ///
  /// In en, this message translates to:
  /// **'Discard and leave'**
  String get txDiscard;

  /// No description provided for @countryLanguageUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Only an English interface is currently available for this country.'**
  String get countryLanguageUnavailable;

  /// No description provided for @darkMode.
  ///
  /// In en, this message translates to:
  /// **'Dark mode'**
  String get darkMode;

  /// No description provided for @darkModeHint.
  ///
  /// In en, this message translates to:
  /// **'Use the dark appearance throughout the app'**
  String get darkModeHint;

  /// No description provided for @liveStartCapture.
  ///
  /// In en, this message translates to:
  /// **'START CAPTURE'**
  String get liveStartCapture;

  /// No description provided for @liveStopCapture.
  ///
  /// In en, this message translates to:
  /// **'STOP CAPTURE'**
  String get liveStopCapture;

  /// No description provided for @liveChannel.
  ///
  /// In en, this message translates to:
  /// **'Channel'**
  String get liveChannel;

  /// No description provided for @liveTransmission.
  ///
  /// In en, this message translates to:
  /// **'Live transmission'**
  String get liveTransmission;

  /// No description provided for @simulatedShort.
  ///
  /// In en, this message translates to:
  /// **'SIM'**
  String get simulatedShort;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en', 'vi'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppLocalizationsEn();
    case 'vi':
      return AppLocalizationsVi();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
