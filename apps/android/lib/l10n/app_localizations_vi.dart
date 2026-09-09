// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Vietnamese (`vi`).
class AppLocalizationsVi extends AppLocalizations {
  AppLocalizationsVi([String locale = 'vi']) : super(locale);

  @override
  String get steeringWheel => 'Vô lăng mô phỏng';

  @override
  String get steeringLeft => 'Trái';

  @override
  String get steeringRight => 'Phải';

  @override
  String get steeringStraight => 'Thẳng';

  @override
  String get steeringCenter => 'Về giữa';

  @override
  String get steeringAuto => 'Tự động — mô phỏng';

  @override
  String get moduleDevices => 'Thiết bị';

  @override
  String get modulePending => 'Chưa tích hợp';

  @override
  String get stationUnavailable => 'Station không còn khả dụng';

  @override
  String get dashboard => 'Dashboard';

  @override
  String get speed => 'Tốc độ';

  @override
  String get depth => 'Độ sâu';

  @override
  String get heading => 'Hướng';

  @override
  String get position => 'Vị trí';

  @override
  String get map => 'Sơ đồ tọa độ';

  @override
  String get control => 'Điều khiển';

  @override
  String get auto => 'Tự động';

  @override
  String get manual => 'Thủ công';

  @override
  String get dashboardStatus => 'Trạng thái';

  @override
  String get stationOnline => 'Station Online';

  @override
  String get stationOffline => 'Station Offline';

  @override
  String get telemetryMock => 'Telemetry mô phỏng';

  @override
  String get controlMock => 'Mô phỏng — chưa kết nối phần cứng';

  @override
  String get mapMockNotice => 'Mô phỏng — không dùng dẫn đường';

  @override
  String get telemetryMissing => 'Telemetry mô phỏng — chờ dữ liệu';

  @override
  String get telemetryFresh => 'Telemetry mô phỏng — đang cập nhật';

  @override
  String get telemetryStale => 'Telemetry mô phỏng — dữ liệu cũ';

  @override
  String get telemetryError => 'Telemetry mô phỏng — lỗi dữ liệu';

  @override
  String get start => 'Bắt đầu';

  @override
  String get stop => 'Dừng';

  @override
  String get starting => 'Đang bật…';

  @override
  String get stopping => 'Đang dừng…';

  @override
  String get waiting => 'Đang chờ trạm';

  @override
  String get history => 'Lịch sử';

  @override
  String get enableLiveAudio => 'Bật tự động phát âm thanh';

  @override
  String get disableLiveAudio => 'Tắt tự động phát âm thanh';

  @override
  String get rxHeard => 'Nghe được';

  @override
  String get rxTranslateTo => 'Dịch sang';

  @override
  String get detecting => 'Đang phát hiện';

  @override
  String get translations => 'Bản dịch trực tiếp';

  @override
  String get emptyTitle => 'Đang chờ tín hiệu thoại';

  @override
  String get emptyBody => 'Bắt đầu thu để nhận transcript và bản dịch.';

  @override
  String get retry => 'Thử lại';

  @override
  String get rxAudioInputNotFound =>
      'Không tìm thấy USB SoundCard đầu vào. Hãy kết nối thiết bị rồi thử lại.';

  @override
  String get rxStartFailed => 'Station không thể khởi động RX.';

  @override
  String get offline => 'Offline quá 15 giây';

  @override
  String get apiReady => 'API READY';

  @override
  String get apiError => 'API ERROR';

  @override
  String get quotaNear => 'Bạn sắp sử dụng hết thời lượng của gói.';

  @override
  String get quotaExhausted => 'Đã sử dụng hết thời lượng của gói.';

  @override
  String get settings => 'Cài đặt';

  @override
  String get uiLanguage => 'Ngôn ngữ giao diện';

  @override
  String get country => 'Quốc gia';

  @override
  String get countryNotSet => 'Chưa chọn';

  @override
  String get countrySearchHint => 'Tìm quốc gia';

  @override
  String get selectCountry => 'Chọn quốc gia';

  @override
  String get selectTimezone => 'Chọn múi giờ';

  @override
  String get countryChangeNotice =>
      'Bản ghi mới sẽ được lưu theo ngày của múi giờ này.';

  @override
  String get stations => 'Trạm của tôi';

  @override
  String get account => 'Tài khoản';

  @override
  String get pairStation => 'Ghép trạm';

  @override
  String get noStation => 'Chưa có trạm';

  @override
  String get noStationBody =>
      'Quét tem QR trên thiết bị hoặc dùng mã tạm thời để ghép trạm.';

  @override
  String get signIn => 'Đăng nhập';

  @override
  String get signUp => 'Đăng ký';

  @override
  String get signingIn => 'Đang xử lý...';

  @override
  String get password => 'Mật khẩu';

  @override
  String get confirmPassword => 'Nhập lại mật khẩu';

  @override
  String get showPassword => 'Hiện mật khẩu';

  @override
  String get hidePassword => 'Ẩn mật khẩu';

  @override
  String get google => 'Tiếp tục với Google';

  @override
  String get googleSignUp => 'Đăng ký bằng Google';

  @override
  String get createAccount => 'Tạo tài khoản';

  @override
  String get authEmailRequired => 'Vui lòng nhập email.';

  @override
  String get authInvalidEmail => 'Email không đúng định dạng.';

  @override
  String get authPasswordRequired => 'Vui lòng nhập mật khẩu.';

  @override
  String get authPasswordRequirements =>
      'Mật khẩu phải có ít nhất 6 ký tự, gồm chữ hoa, chữ cái và chữ số.';

  @override
  String get authConfirmRequired => 'Vui lòng nhập lại mật khẩu.';

  @override
  String get authPasswordMismatch => 'Mật khẩu nhập lại không khớp.';

  @override
  String get authInvalidCredentials => 'Email hoặc mật khẩu không đúng.';

  @override
  String get authEmailInUse => 'Email này đã được sử dụng.';

  @override
  String get authWeakPassword => 'Mật khẩu chưa đủ mạnh.';

  @override
  String get authUserDisabled => 'Tài khoản này đã bị khóa.';

  @override
  String get authTooManyRequests =>
      'Có quá nhiều yêu cầu. Vui lòng thử lại sau.';

  @override
  String get authNetworkError => 'Không thể kết nối. Hãy kiểm tra mạng.';

  @override
  String get authGoogleError => 'Không thể đăng nhập bằng Google.';

  @override
  String get authUnknownError => 'Không thể xác thực. Vui lòng thử lại.';

  @override
  String get verifyEmailTitle => 'Xác minh email';

  @override
  String verifyEmailBody(Object email) {
    return 'Chúng tôi đã gửi liên kết xác minh đến $email. Hãy mở email trước khi tiếp tục.';
  }

  @override
  String get verificationCheck => 'Tôi đã xác minh';

  @override
  String get verificationStillPending => 'Email vẫn chưa được xác minh.';

  @override
  String get verificationResent => 'Đã gửi lại email xác minh.';

  @override
  String verificationResendWait(Object seconds) {
    return 'Gửi lại sau $seconds giây';
  }

  @override
  String get confirmSignOut => 'Đăng xuất?';

  @override
  String get confirmSignOutBody =>
      'Bạn có chắc muốn đăng xuất khỏi PRANA ELEX?';

  @override
  String get tagline => 'Theo dõi và điều khiển trạm VHF của bạn.';

  @override
  String get accountPlan => 'Tài khoản và gói';

  @override
  String get signOut => 'Đăng xuất';

  @override
  String get emailVerified => 'Email đã xác minh';

  @override
  String get emailUnverified => 'Email chưa xác minh';

  @override
  String get resendVerification => 'Gửi lại email xác minh';

  @override
  String get deviceLabel => 'Tem thiết bị';

  @override
  String get temporaryCode => 'Mã tạm thời';

  @override
  String get scanQr => 'Mở camera quét QR';

  @override
  String get close => 'Đóng';

  @override
  String get loadStationError => 'Không tải được trạm';

  @override
  String get noHistoryDays => 'Chưa có lịch sử dịch';

  @override
  String get noHistoryDaysBody => 'Các ngày có bản dịch sẽ xuất hiện tại đây.';

  @override
  String historyDayTitle(Object date) {
    return 'Ngày $date';
  }

  @override
  String historyDaySummary(Object count, Object range) {
    return '$count log • $range';
  }

  @override
  String get syncing => 'Đang đồng bộ';

  @override
  String get connectStation => 'Kết nối PRANA Station';

  @override
  String get labelHelp =>
      'Quét tem QR cố định được dán trên Raspberry Pi hoặc Laptop.';

  @override
  String get temporaryHelp =>
      'Dùng mã tạm thời do Laptop hoặc station cũ tạo ra.';

  @override
  String get activationHelp => '16 ký tự, tự động chia thành 4 nhóm';

  @override
  String get stationMissing => 'Trạm không còn tồn tại';

  @override
  String get realtimeError => 'Mất kết nối realtime';

  @override
  String get invalidPairingQr => 'QR này không phải mã ghép PRANA ELEX.';

  @override
  String get invalidActivation =>
      'Nhập Setup ID 10 ký tự và Activation Code 16 ký tự.';

  @override
  String get invalidTemporaryPairing =>
      'Nhập Pairing ID và mã tạm thời 8 ký tự.';

  @override
  String get stationSettings => 'Cài đặt trạm';

  @override
  String get captureMode => 'Chế độ thu';

  @override
  String get audioDevice => 'Thiết bị âm thanh';

  @override
  String get refreshDevices => 'Quét lại thiết bị';

  @override
  String get deviceScanChanged => 'Đã cập nhật danh sách thiết bị.';

  @override
  String get deviceScanUnchanged => 'Đã quét xong, danh sách không thay đổi.';

  @override
  String get deviceScanTimeout =>
      'Station chưa phản hồi kết quả quét. Hãy kiểm tra kết nối.';

  @override
  String get audioSource => 'Nguồn thu';

  @override
  String get txOutputDevice => 'Thiết bị phát (TX)';

  @override
  String get txOutputVia => 'Phát TX qua';

  @override
  String get txStartRequiredShort => 'HÃY START';

  @override
  String get txTranslationEditHint =>
      'Chỉnh nội dung sẽ được phát trước khi gửi';

  @override
  String get stationInformation => 'Thông tin Station';

  @override
  String get stationCode => 'Mã trạm';

  @override
  String get stationCodeHint =>
      'Gửi mã này cho nhà sản xuất khi cần trích xuất ghi âm.';

  @override
  String get stationCodeCopied => 'Đã chép mã trạm';

  @override
  String get copy => 'Chép';

  @override
  String get storagePath => 'Thư mục lưu trên Station';

  @override
  String get activeCapture => 'Cấu hình đang hoạt động';

  @override
  String get lastDeviceScan => 'Lần quét thiết bị gần nhất';

  @override
  String get capabilitiesUnavailable =>
      'Station chưa gửi danh sách thiết bị âm thanh.';

  @override
  String get save => 'Lưu thay đổi';

  @override
  String get savingChanges => 'Đang lưu…';

  @override
  String get applyingChanges => 'Đang áp dụng…';

  @override
  String get settingsSyncDelayed =>
      'Đã lưu thay đổi nhưng dữ liệu realtime chưa đồng bộ. Ứng dụng sẽ tiếp tục chờ để tránh gửi lệnh trùng.';

  @override
  String get historySearch => 'Tìm nội dung hoặc bản dịch';

  @override
  String get txHistoryEmpty => 'Chưa có lịch sử TX';

  @override
  String get txHistoryEmptyBody =>
      'Các lượt TX đã xác nhận sẽ xuất hiện tại đây.';

  @override
  String get txHistoryEdited => 'Đã chỉnh sửa';

  @override
  String txHistoryAttempt(Object attempt) {
    return 'Lần gửi $attempt';
  }

  @override
  String get playAudio => 'Phát âm thanh';

  @override
  String get txStatusSynthesizing => 'Đang tạo audio';

  @override
  String get txStatusQueued => 'Đang chờ';

  @override
  String get txStatusClaimed => 'Đã nhận';

  @override
  String get txStatusTransmitting => 'Đang phát';

  @override
  String get txStatusCompleted => 'Hoàn tất';

  @override
  String get txStatusFailed => 'Thất bại';

  @override
  String get forgotPassword => 'Quên mật khẩu';

  @override
  String get resetPassword => 'Gửi email đặt lại mật khẩu';

  @override
  String get resetPasswordShort => 'Đặt lại mật khẩu';

  @override
  String get resetSent =>
      'Đã gửi email đặt lại mật khẩu nếu tài khoản tồn tại.';

  @override
  String get linked => 'Đã liên kết';

  @override
  String get notLinked => 'Chưa liên kết';

  @override
  String get linkGoogle => 'Liên kết Google';

  @override
  String get usage => 'Mức sử dụng';

  @override
  String get plans => 'Gói dịch vụ';

  @override
  String get changePlan => 'Đổi gói';

  @override
  String get collapse => 'Thu gọn';

  @override
  String get seconds => 'giây';

  @override
  String get devices => 'Thiết bị và trạm';

  @override
  String get confirmRevoke => 'Xác nhận thu hồi';

  @override
  String get revoke => 'Thu hồi';

  @override
  String get confirmRemoveStation => 'Gỡ Station?';

  @override
  String get removeStation => 'Gỡ Station';

  @override
  String removeStationBody(Object name) {
    return 'Gỡ $name khỏi tài khoản này? Station sẽ dừng và tem QR có thể được tài khoản khác quét để ghép lại.';
  }

  @override
  String get errorStationNotPaired =>
      'Station chưa được ghép với tài khoản. Hãy quét tem QR.';

  @override
  String get errorStationRevoked =>
      'Station đã bị khóa. Quản trị viên cần gỡ Station để cho phép ghép lại.';

  @override
  String get errorStationLimitReached =>
      'Tài khoản đã đạt giới hạn số Station của gói hiện tại.';

  @override
  String get errorActivationInvalid =>
      'Setup ID hoặc Activation Code không hợp lệ.';

  @override
  String get errorStationAlreadyClaimed =>
      'Station đang thuộc một tài khoản khác.';

  @override
  String get done => 'Đã hoàn tất';

  @override
  String historyRestricted(Object days) {
    return 'Kết quả mới được giới hạn theo gói. Toàn bộ lịch sử sẽ mở khóa sau $days ngày.';
  }

  @override
  String get errorConnectionTimeout =>
      'Không thể kết nối PRANA API. Nếu dùng điện thoại thật, hãy kiểm tra API_URL không còn là 10.0.2.2.';

  @override
  String get errorRequestTimeout => 'PRANA API phản hồi quá chậm. Hãy thử lại.';

  @override
  String get errorApiUnreachable =>
      'Không thể truy cập PRANA API. Kiểm tra mạng và địa chỉ máy chủ.';

  @override
  String get errorRequestFailed => 'Không thể thực hiện yêu cầu. Hãy thử lại.';

  @override
  String processingRetrying(Object attempt) {
    return 'Máy chủ đang bận, đang thử lại ($attempt/3)…';
  }

  @override
  String get speakTranslation => 'Nghe bản dịch';

  @override
  String get stopSpeaking => 'Dừng phát';

  @override
  String get ttsLanguageUnavailable =>
      'Điện thoại chưa có giọng đọc cho ngôn ngữ này. Hãy cài dữ liệu Text-to-Speech trong Cài đặt Android.';

  @override
  String get ttsPlaybackError =>
      'Không thể phát giọng nói. Hãy kiểm tra công cụ Text-to-Speech của điện thoại.';

  @override
  String get txTitle => 'Phát bản dịch qua VHF';

  @override
  String get txSubtitle =>
      'Giữ PTT để nói, sau đó xem lại bản dịch trước khi phát.';

  @override
  String get txHoldToTalk => 'GIỮ ĐỂ NÓI';

  @override
  String get txReleaseToStop => 'THẢ ĐỂ DỪNG';

  @override
  String get txTransmitIn => 'Phát bằng';

  @override
  String get txReviewShort => 'XEM LẠI';

  @override
  String get txDoneShort => 'HOÀN TẤT';

  @override
  String get txProcessingShort => 'ĐANG DỊCH';

  @override
  String get txQueuedShort => 'ĐANG CHỜ';

  @override
  String get txTransmittingShort => 'ĐANG PHÁT';

  @override
  String get txRecording => 'Đang thu giọng nói';

  @override
  String get txPttHint => 'Giữ nút trong khi nói. Nhả nút để tạo bản dịch.';

  @override
  String txMaxDuration(Object seconds) {
    return 'Tối đa $seconds giây mỗi lần.';
  }

  @override
  String get txProcessing => 'Đang tạo bản dịch';

  @override
  String get txProcessingBody =>
      'PRANA đang nhận dạng, dịch và chuẩn bị giọng phát mẫu.';

  @override
  String get txReviewTitle => 'Kiểm tra trước khi phát';

  @override
  String get txTranscript => 'Nội dung đã nhận dạng';

  @override
  String get txTranslation => 'Bản dịch sẽ phát';

  @override
  String get txTransmit => 'Phát qua VHF';

  @override
  String get txCancel => 'Hủy bản nháp';

  @override
  String get txQueued => 'Đang chờ Station';

  @override
  String get txQueuedBody => 'Bản dịch đã sẵn sàng và đang chờ lượt phát.';

  @override
  String get txTransmitting => 'Station đang phát';

  @override
  String get txTransmittingBody =>
      'RX tạm dừng trong khi tín hiệu TX được phát.';

  @override
  String get txCompleted => 'Đã phát xong';

  @override
  String get txCompletedBody => 'Station đã nhả PTT và quay lại chế độ RX.';

  @override
  String get txNewMessage => 'Tạo bản phát mới';

  @override
  String get txStationOffline => 'Station đang offline. Không thể bắt đầu TX.';

  @override
  String get txStationOfflineDuringTx =>
      'Mất kết nối với Station khi đang phát. Kết quả TX chưa được xác nhận.';

  @override
  String get txPttUnavailable =>
      'Không thể điều khiển PTT. Hãy kiểm tra GPIO hoặc cấu hình Station.';

  @override
  String get txRetryWaitingStation =>
      'Chờ Station online và xác nhận job thất bại trước khi thử lại.';

  @override
  String get txRecordingShort => 'ĐANG THU';

  @override
  String get txReleaseHint => 'Thả để kết thúc';

  @override
  String get txStationBusy => 'Station đang được một thiết bị khác sử dụng.';

  @override
  String get txChannelBusy => 'Kênh VHF đang bận. Bản phát đã được hủy.';

  @override
  String get txExpired => 'Phiên TX đã hết hạn. Vui lòng thu lại.';

  @override
  String get txProcessingFailed => 'Không thể tạo bản dịch. Vui lòng thử lại.';

  @override
  String get txAudioTooLong =>
      'Bản thu vượt quá thời lượng cho phép. Vui lòng thu lại.';

  @override
  String get txOutputTooLong =>
      'Audio sau khi dịch vượt quá 120 giây. Hãy rút gọn nội dung rồi thử lại.';

  @override
  String get txSynthesisTimeout =>
      'Quá thời gian tạo audio TX. Job đã dừng an toàn; hãy thử lại thủ công.';

  @override
  String get txPlaybackTimeout =>
      'Quá thời gian phát TX. PTT đã được nhả an toàn; hãy kiểm tra Station.';

  @override
  String get txTransmissionFailed => 'Station không thể phát bản dịch.';

  @override
  String get txDiscardTitle => 'Hủy bản TX hiện tại?';

  @override
  String get txDiscardBody => 'Bản thu hoặc bản dịch chưa phát sẽ bị xóa.';

  @override
  String get txDiscard => 'Hủy và rời đi';

  @override
  String get countryLanguageUnavailable =>
      'Hiện chỉ có giao diện tiếng Anh cho quốc gia này.';

  @override
  String get darkMode => 'Chế độ tối';

  @override
  String get darkModeHint => 'Dùng giao diện tối trong toàn bộ ứng dụng';
}
