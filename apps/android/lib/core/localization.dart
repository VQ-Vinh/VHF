import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class AppLocaleController extends ChangeNotifier {
  AppLocaleController(this._storage) {
    _load();
  }

  static const _key = 'app_locale';
  final FlutterSecureStorage _storage;
  Locale? locale;

  Future<void> _load() async {
    final value = await _storage.read(key: _key);
    if (value == 'en' || value == 'vi') {
      locale = Locale(value!);
      notifyListeners();
    }
  }

  Future<void> setLocale(String code) async {
    locale = Locale(code);
    notifyListeners();
    await _storage.write(key: _key, value: code);
  }
}

abstract final class AppText {
  static const supportedLocales = [Locale('vi'), Locale('en')];

  static const _values = <String, Map<String, String>>{
    'vi': {
      'start': 'Bắt đầu',
      'stop': 'Dừng',
      'starting': 'Đang bật…',
      'stopping': 'Đang dừng…',
      'waiting': 'Đang chờ trạm',
      'history': 'Lịch sử',
      'enable_live_audio': 'Bật tự động phát âm thanh',
      'disable_live_audio': 'Tắt tự động phát âm thanh',
      'rx_heard': 'Nghe được',
      'rx_translate_to': 'Dịch sang',
      'detecting': 'Đang phát hiện',
      'translations': 'Bản dịch trực tiếp',
      'empty_title': 'Đang chờ tín hiệu thoại',
      'empty_body': 'Bắt đầu thu để nhận transcript và bản dịch.',
      'retry': 'Thử lại',
      'rx_audio_input_not_found':
          'Không tìm thấy USB SoundCard đầu vào. Hãy kết nối thiết bị rồi thử lại.',
      'rx_start_failed': 'Station không thể khởi động RX.',
      'offline': 'Offline quá 15 giây',
      'api_ready': 'API READY',
      'api_error': 'API ERROR',
      'quota_near': 'Bạn sắp sử dụng hết thời lượng của gói.',
      'quota_exhausted': 'Đã sử dụng hết thời lượng của gói.',
      'settings': 'Cài đặt',
      'ui_language': 'Ngôn ngữ giao diện',
      'country': 'Quốc gia',
      'country_not_set': 'Chưa chọn',
      'country_search_hint': 'Tìm quốc gia',
      'select_country': 'Chọn quốc gia',
      'select_timezone': 'Chọn múi giờ',
      'country_change_notice':
          'Bản ghi mới sẽ được lưu theo ngày của múi giờ này.',
      'stations': 'Trạm của tôi',
      'account': 'Tài khoản',
      'pair_station': 'Ghép trạm',
      'no_station': 'Chưa có trạm',
      'no_station_body':
          'Quét tem QR trên thiết bị hoặc dùng mã tạm thời để ghép trạm.',
      'sign_in': 'Đăng nhập',
      'sign_up': 'Đăng ký',
      'signing_in': 'Đang xử lý...',
      'password': 'Mật khẩu',
      'confirm_password': 'Nhập lại mật khẩu',
      'show_password': 'Hiện mật khẩu',
      'hide_password': 'Ẩn mật khẩu',
      'google': 'Tiếp tục với Google',
      'google_sign_up': 'Đăng ký bằng Google',
      'create_account': 'Tạo tài khoản',
      'auth_email_required': 'Vui lòng nhập email.',
      'auth_invalid_email': 'Email không đúng định dạng.',
      'auth_password_required': 'Vui lòng nhập mật khẩu.',
      'auth_password_requirements':
          'Mật khẩu phải có ít nhất 6 ký tự, gồm chữ hoa, chữ cái và chữ số.',
      'auth_confirm_required': 'Vui lòng nhập lại mật khẩu.',
      'auth_password_mismatch': 'Mật khẩu nhập lại không khớp.',
      'auth_invalid_credentials': 'Email hoặc mật khẩu không đúng.',
      'auth_email_in_use': 'Email này đã được sử dụng.',
      'auth_weak_password': 'Mật khẩu chưa đủ mạnh.',
      'auth_user_disabled': 'Tài khoản này đã bị khóa.',
      'auth_too_many_requests': 'Có quá nhiều yêu cầu. Vui lòng thử lại sau.',
      'auth_network_error': 'Không thể kết nối. Hãy kiểm tra mạng.',
      'auth_google_error': 'Không thể đăng nhập bằng Google.',
      'auth_unknown_error': 'Không thể xác thực. Vui lòng thử lại.',
      'verify_email_title': 'Xác minh email',
      'verify_email_body':
          'Chúng tôi đã gửi liên kết xác minh đến {email}. Hãy mở email trước khi tiếp tục.',
      'verification_check': 'Tôi đã xác minh',
      'verification_still_pending': 'Email vẫn chưa được xác minh.',
      'verification_resent': 'Đã gửi lại email xác minh.',
      'verification_resend_wait': 'Gửi lại sau {seconds} giây',
      'confirm_sign_out': 'Đăng xuất?',
      'confirm_sign_out_body': 'Bạn có chắc muốn đăng xuất khỏi PRANA ELEX?',
      'tagline': 'Theo dõi và điều khiển trạm VHF của bạn.',
      'account_plan': 'Tài khoản và gói',
      'environment': 'Môi trường',
      'sign_out': 'Đăng xuất',
      'email_verified': 'Email đã xác minh',
      'email_unverified': 'Email chưa xác minh',
      'resend_verification': 'Gửi lại email xác minh',
      'device_label': 'Tem thiết bị',
      'temporary_code': 'Mã tạm thời',
      'scan_qr': 'Mở camera quét QR',
      'close': 'Đóng',
      'load_station_error': 'Không tải được trạm',
      'no_history_days': 'Chưa có lịch sử dịch',
      'no_history_days_body': 'Các ngày có bản dịch sẽ xuất hiện tại đây.',
      'history_day_title': 'Ngày {date}',
      'history_day_summary': '{count} log • {range}',
      'syncing': 'Đang đồng bộ',
      'connect_station': 'Kết nối PRANA Station',
      'label_help':
          'Quét tem QR cố định được dán trên Raspberry Pi hoặc Laptop.',
      'temporary_help': 'Dùng mã tạm thời do Laptop hoặc station cũ tạo ra.',
      'activation_help': '16 ký tự, tự động chia thành 4 nhóm',
      'station_missing': 'Trạm không còn tồn tại',
      'realtime_error': 'Mất kết nối realtime',
      'invalid_pairing_qr': 'QR này không phải mã ghép PRANA ELEX.',
      'invalid_activation':
          'Nhập Setup ID 10 ký tự và Activation Code 16 ký tự.',
      'invalid_temporary_pairing': 'Nhập Pairing ID và mã tạm thời 8 ký tự.',
      'station_settings': 'Cài đặt trạm',
      'capture_mode': 'Chế độ thu',
      'audio_device': 'Thiết bị âm thanh',
      'refresh_devices': 'Quét lại thiết bị',
      'device_scan_changed': 'Đã cập nhật danh sách thiết bị.',
      'device_scan_unchanged': 'Đã quét xong, danh sách không thay đổi.',
      'device_scan_timeout':
          'Station chưa phản hồi kết quả quét. Hãy kiểm tra kết nối.',
      'audio_source': 'Nguồn thu',
      'tx_output': 'Đầu ra TX',
      'tx_output_device': 'Thiết bị phát âm thanh trên Laptop',
      'tx_start_required_short': 'HÃY START',
      'tx_translation_edit_hint': 'Chỉnh nội dung sẽ được phát trước khi gửi',
      'station_information': 'Thông tin Station',
      'storage_path': 'Thư mục lưu trên Station',
      'active_capture': 'Cấu hình đang hoạt động',
      'last_device_scan': 'Lần quét thiết bị gần nhất',
      'capabilities_unavailable':
          'Station chưa gửi danh sách thiết bị âm thanh.',
      'save': 'Lưu thay đổi',
      'saving_changes': 'Đang lưu…',
      'applying_changes': 'Đang áp dụng…',
      'settings_sync_delayed':
          'Đã lưu thay đổi nhưng dữ liệu realtime chưa đồng bộ. '
          'Ứng dụng sẽ tiếp tục chờ để tránh gửi lệnh trùng.',
      'history_search': 'Tìm nội dung hoặc bản dịch',
      'tx_history_empty': 'Chưa có lịch sử TX',
      'tx_history_empty_body': 'Các lượt TX đã xác nhận sẽ xuất hiện tại đây.',
      'tx_history_edited': 'Đã chỉnh sửa',
      'tx_history_attempt': 'Lần gửi {attempt}',
      'play_audio': 'Phát âm thanh',
      'tx_status_synthesizing': 'Đang tạo audio',
      'tx_status_queued': 'Đang chờ',
      'tx_status_claimed': 'Đã nhận',
      'tx_status_transmitting': 'Đang phát',
      'tx_status_completed': 'Hoàn tất',
      'tx_status_failed': 'Thất bại',
      'forgot_password': 'Quên mật khẩu',
      'reset_password': 'Gửi email đặt lại mật khẩu',
      'reset_password_short': 'Đặt lại mật khẩu',
      'reset_sent': 'Đã gửi email đặt lại mật khẩu nếu tài khoản tồn tại.',
      'linked': 'Đã liên kết',
      'not_linked': 'Chưa liên kết',
      'link_google': 'Liên kết Google',
      'usage': 'Mức sử dụng',
      'plans': 'Gói dịch vụ',
      'change_plan': 'Đổi gói',
      'collapse': 'Thu gọn',
      'seconds': 'giây',
      'devices': 'Thiết bị và trạm',
      'confirm_revoke': 'Xác nhận thu hồi',
      'revoke': 'Thu hồi',
      'confirm_remove_station': 'Gỡ Station?',
      'remove_station': 'Gỡ Station',
      'remove_station_body':
          'Gỡ {name} khỏi tài khoản này? Station sẽ dừng và tem QR có thể được tài khoản khác quét để ghép lại.',
      'error_station_not_paired':
          'Station chưa được ghép với tài khoản. Hãy quét tem QR.',
      'error_station_revoked':
          'Station đã bị khóa. Quản trị viên cần gỡ Station để cho phép ghép lại.',
      'error_station_limit_reached':
          'Tài khoản đã đạt giới hạn số Station của gói hiện tại.',
      'error_activation_invalid': 'Setup ID hoặc Activation Code không hợp lệ.',
      'error_station_already_claimed': 'Station đang thuộc một tài khoản khác.',
      'done': 'Đã hoàn tất',
      'history_restricted':
          'Kết quả mới được giới hạn theo gói. Toàn bộ lịch sử sẽ mở khóa sau {days} ngày.',
      'error_connection_timeout':
          'Không thể kết nối PRANA API. Nếu dùng điện thoại thật, hãy kiểm tra API_URL không còn là 10.0.2.2.',
      'error_request_timeout': 'PRANA API phản hồi quá chậm. Hãy thử lại.',
      'error_api_unreachable':
          'Không thể truy cập PRANA API. Kiểm tra mạng và địa chỉ máy chủ.',
      'error_request_failed': 'Không thể thực hiện yêu cầu. Hãy thử lại.',
      'processing_retrying': 'Máy chủ đang bận, đang thử lại ({attempt}/3)…',
      'speak_translation': 'Nghe bản dịch',
      'stop_speaking': 'Dừng phát',
      'tts_language_unavailable':
          'Điện thoại chưa có giọng đọc cho ngôn ngữ này. Hãy cài dữ liệu Text-to-Speech trong Cài đặt Android.',
      'tts_playback_error':
          'Không thể phát giọng nói. Hãy kiểm tra công cụ Text-to-Speech của điện thoại.',
      'tx_title': 'Phát bản dịch qua VHF',
      'tx_subtitle': 'Giữ PTT để nói, sau đó xem lại bản dịch trước khi phát.',
      'tx_hold_to_talk': 'GIỮ ĐỂ NÓI',
      'tx_release_to_stop': 'THẢ ĐỂ DỪNG',
      'tx_transmit_in': 'Phát bằng',
      'tx_review_short': 'XEM LẠI',
      'tx_done_short': 'HOÀN TẤT',
      'tx_processing_short': 'ĐANG DỊCH',
      'tx_queued_short': 'ĐANG CHỜ',
      'tx_transmitting_short': 'ĐANG PHÁT',
      'tx_recording': 'Đang thu giọng nói',
      'tx_ptt_hint': 'Giữ nút trong khi nói. Nhả nút để tạo bản dịch.',
      'tx_max_duration': 'Tối đa {seconds} giây mỗi lần.',
      'tx_processing': 'Đang tạo bản dịch',
      'tx_processing_body':
          'PRANA đang nhận dạng, dịch và chuẩn bị giọng phát mẫu.',
      'tx_review_title': 'Kiểm tra trước khi phát',
      'tx_transcript': 'Nội dung đã nhận dạng',
      'tx_translation': 'Bản dịch sẽ phát',
      'tx_transmit': 'Phát qua VHF',
      'tx_cancel': 'Hủy bản nháp',
      'tx_queued': 'Đang chờ Station',
      'tx_queued_body': 'Bản dịch đã sẵn sàng và đang chờ lượt phát.',
      'tx_transmitting': 'Station đang phát',
      'tx_transmitting_body': 'RX tạm dừng trong khi tín hiệu TX được phát.',
      'tx_completed': 'Đã phát xong',
      'tx_completed_body': 'Station đã nhả PTT và quay lại chế độ RX.',
      'tx_new_message': 'Tạo bản phát mới',
      'tx_station_offline': 'Station đang offline. Không thể bắt đầu TX.',
      'tx_station_offline_during_tx':
          'Mất kết nối với Station khi đang phát. Kết quả TX chưa được xác nhận.',
      'tx_ptt_unavailable':
          'Không thể điều khiển PTT. Hãy kiểm tra GPIO hoặc cấu hình Station.',
      'tx_retry_waiting_station':
          'Chờ Station online và xác nhận job thất bại trước khi thử lại.',
      'tx_recording_short': 'ĐANG THU',
      'tx_release_hint': 'Thả để kết thúc',
      'tx_station_busy': 'Station đang được một thiết bị khác sử dụng.',
      'tx_channel_busy': 'Kênh VHF đang bận. Bản phát đã được hủy.',
      'tx_expired': 'Phiên TX đã hết hạn. Vui lòng thu lại.',
      'tx_processing_failed': 'Không thể tạo bản dịch. Vui lòng thử lại.',
      'tx_audio_too_long':
          'Bản thu vượt quá thời lượng cho phép. Vui lòng thu lại.',
      'tx_output_too_long':
          'Audio sau khi dịch vượt quá 120 giây. Hãy rút gọn nội dung rồi thử lại.',
      'tx_synthesis_timeout':
          'Quá thời gian tạo audio TX. Job đã dừng an toàn; hãy thử lại thủ công.',
      'tx_playback_timeout':
          'Quá thời gian phát TX. PTT đã được nhả an toàn; hãy kiểm tra Station.',
      'tx_transmission_failed': 'Station không thể phát bản dịch.',
      'tx_discard_title': 'Hủy bản TX hiện tại?',
      'tx_discard_body': 'Bản thu hoặc bản dịch chưa phát sẽ bị xóa.',
      'tx_discard': 'Hủy và rời đi',
    },
    'en': {
      'start': 'Start',
      'stop': 'Stop',
      'starting': 'Starting…',
      'stopping': 'Stopping…',
      'waiting': 'Waiting for station',
      'history': 'History',
      'enable_live_audio': 'Enable automatic audio playback',
      'disable_live_audio': 'Disable automatic audio playback',
      'rx_heard': 'Heard',
      'rx_translate_to': 'Translate to',
      'detecting': 'Detecting',
      'translations': 'Live translations',
      'empty_title': 'Waiting for speech',
      'empty_body': 'Start capture to receive transcript and translation.',
      'retry': 'Retry',
      'rx_audio_input_not_found':
          'No USB SoundCard input was found. Connect the device and try again.',
      'rx_start_failed': 'The Station could not start RX.',
      'offline': 'Offline for more than 15 seconds',
      'api_ready': 'API READY',
      'api_error': 'API ERROR',
      'quota_near': 'You are nearing your plan usage limit.',
      'quota_exhausted': 'Your plan usage limit has been reached.',
      'settings': 'Settings',
      'ui_language': 'Interface language',
      'country': 'Country',
      'country_not_set': 'Not set',
      'country_search_hint': 'Search countries',
      'select_country': 'Select country',
      'select_timezone': 'Select timezone',
      'country_change_notice':
          'New recordings are stored under this timezone\'s date.',
      'stations': 'My stations',
      'account': 'Account',
      'pair_station': 'Pair station',
      'no_station': 'No stations yet',
      'no_station_body':
          'Scan the device QR label or use a temporary pairing code.',
      'sign_in': 'Sign in',
      'sign_up': 'Sign up',
      'signing_in': 'Working...',
      'password': 'Password',
      'confirm_password': 'Confirm password',
      'show_password': 'Show password',
      'hide_password': 'Hide password',
      'google': 'Continue with Google',
      'google_sign_up': 'Sign up with Google',
      'create_account': 'Create account',
      'auth_email_required': 'Enter your email.',
      'auth_invalid_email': 'Enter a valid email address.',
      'auth_password_required': 'Enter your password.',
      'auth_password_requirements':
          'Use at least 6 characters with an uppercase letter, a letter, and a number.',
      'auth_confirm_required': 'Confirm your password.',
      'auth_password_mismatch': 'The passwords do not match.',
      'auth_invalid_credentials': 'The email or password is incorrect.',
      'auth_email_in_use': 'This email is already in use.',
      'auth_weak_password': 'The password is too weak.',
      'auth_user_disabled': 'This account has been disabled.',
      'auth_too_many_requests': 'Too many attempts. Try again later.',
      'auth_network_error': 'Unable to connect. Check your network.',
      'auth_google_error': 'Unable to sign in with Google.',
      'auth_unknown_error': 'Authentication failed. Please try again.',
      'verify_email_title': 'Verify your email',
      'verify_email_body':
          'We sent a verification link to {email}. Open it before continuing.',
      'verification_check': 'I have verified',
      'verification_still_pending': 'Your email is not verified yet.',
      'verification_resent': 'A new verification email was sent.',
      'verification_resend_wait': 'Resend in {seconds} seconds',
      'confirm_sign_out': 'Sign out?',
      'confirm_sign_out_body':
          'Are you sure you want to sign out of PRANA ELEX?',
      'tagline': 'Monitor and control your VHF stations.',
      'account_plan': 'Account and plan',
      'environment': 'Environment',
      'sign_out': 'Sign out',
      'email_verified': 'Email verified',
      'email_unverified': 'Email not verified',
      'resend_verification': 'Resend verification email',
      'device_label': 'Device label',
      'temporary_code': 'Temporary code',
      'scan_qr': 'Open QR scanner',
      'close': 'Close',
      'load_station_error': 'Unable to load stations',
      'no_history_days': 'No translation history yet',
      'no_history_days_body': 'Days containing translations will appear here.',
      'history_day_title': 'Date {date}',
      'history_day_summary': '{count} logs • {range}',
      'syncing': 'Synchronizing',
      'connect_station': 'Connect PRANA Station',
      'label_help':
          'Scan the fixed QR label attached to the Raspberry Pi or Laptop.',
      'temporary_help':
          'Use a temporary code created by a Laptop or legacy station.',
      'activation_help':
          '16 characters, grouped automatically in blocks of four',
      'station_missing': 'Station no longer exists',
      'realtime_error': 'Realtime connection lost',
      'invalid_pairing_qr': 'This is not a PRANA ELEX pairing QR code.',
      'invalid_activation':
          'Enter a 10-character Setup ID and 16-character Activation Code.',
      'invalid_temporary_pairing':
          'Enter a Pairing ID and an 8-character temporary code.',
      'station_settings': 'Station settings',
      'capture_mode': 'Capture mode',
      'audio_device': 'Audio device',
      'refresh_devices': 'Refresh devices',
      'device_scan_changed': 'The device list has been updated.',
      'device_scan_unchanged': 'Scan complete. No device changes found.',
      'device_scan_timeout':
          'The Station did not return scan results. Check its connection.',
      'audio_source': 'Audio source',
      'tx_output': 'TX output',
      'tx_output_device': 'Laptop audio output',
      'tx_start_required_short': 'START FIRST',
      'tx_translation_edit_hint':
          'Edit the text that will be spoken before sending',
      'station_information': 'Station information',
      'storage_path': 'Station storage path',
      'active_capture': 'Active capture configuration',
      'last_device_scan': 'Last device scan',
      'capabilities_unavailable':
          'The Station has not reported audio capabilities.',
      'save': 'Save changes',
      'saving_changes': 'Saving…',
      'applying_changes': 'Applying…',
      'settings_sync_delayed':
          'Changes were saved, but realtime data has not synchronized yet. '
          'The app will keep waiting to avoid a duplicate command.',
      'history_search': 'Search transcripts or translations',
      'tx_history_empty': 'No TX history yet',
      'tx_history_empty_body': 'Confirmed TX transmissions will appear here.',
      'tx_history_edited': 'Edited',
      'tx_history_attempt': 'Attempt {attempt}',
      'play_audio': 'Play audio',
      'tx_status_synthesizing': 'Synthesizing',
      'tx_status_queued': 'Queued',
      'tx_status_claimed': 'Claimed',
      'tx_status_transmitting': 'Transmitting',
      'tx_status_completed': 'Completed',
      'tx_status_failed': 'Failed',
      'forgot_password': 'Forgot password',
      'reset_password': 'Send password reset email',
      'reset_password_short': 'Reset password',
      'reset_sent': 'A password reset email was sent if the account exists.',
      'linked': 'Linked',
      'not_linked': 'Not linked',
      'link_google': 'Link Google',
      'usage': 'Usage',
      'plans': 'Plans',
      'change_plan': 'Change plan',
      'collapse': 'Collapse',
      'seconds': 'seconds',
      'devices': 'Devices and stations',
      'confirm_revoke': 'Confirm revoke',
      'revoke': 'Revoke',
      'confirm_remove_station': 'Remove Station?',
      'remove_station': 'Remove Station',
      'remove_station_body':
          'Remove {name} from this account? The Station will stop and its QR label can be scanned by another account.',
      'error_station_not_paired':
          'The Station is not paired with an account. Scan its QR label.',
      'error_station_revoked':
          'The Station is locked. An administrator must release it before it can be paired again.',
      'error_station_limit_reached':
          'This account has reached its Station limit for the current plan.',
      'error_activation_invalid': 'The Setup ID or Activation Code is invalid.',
      'error_station_already_claimed':
          'The Station already belongs to another account.',
      'done': 'Completed',
      'history_restricted':
          'Recent results are limited by your plan. Full history unlocks after {days} day(s).',
      'error_connection_timeout':
          'Cannot connect to PRANA API. On a physical phone, make sure API_URL is not 10.0.2.2.',
      'error_request_timeout': 'PRANA API took too long to respond. Try again.',
      'error_api_unreachable':
          'PRANA API is unreachable. Check the network and server address.',
      'error_request_failed': 'The request could not be completed. Try again.',
      'processing_retrying': 'The server is busy, retrying ({attempt}/3)…',
      'speak_translation': 'Speak translation',
      'stop_speaking': 'Stop speaking',
      'tts_language_unavailable':
          'This phone has no voice for that language. Install Text-to-Speech data in Android settings.',
      'tts_playback_error':
          'Speech playback failed. Check the phone Text-to-Speech engine.',
      'tx_title': 'Transmit a translation over VHF',
      'tx_subtitle':
          'Hold PTT to speak, then review the translation before transmission.',
      'tx_hold_to_talk': 'HOLD TO TALK',
      'tx_release_to_stop': 'RELEASE TO STOP',
      'tx_transmit_in': 'Transmit in',
      'tx_review_short': 'REVIEW',
      'tx_done_short': 'DONE',
      'tx_processing_short': 'TRANSLATING',
      'tx_queued_short': 'QUEUED',
      'tx_transmitting_short': 'TRANSMITTING',
      'tx_recording': 'Recording voice',
      'tx_ptt_hint':
          'Hold the button while speaking. Release it to create a translation.',
      'tx_max_duration': 'Maximum {seconds} seconds per transmission.',
      'tx_processing': 'Preparing translation',
      'tx_processing_body':
          'PRANA is transcribing, translating, and preparing a sample voice.',
      'tx_review_title': 'Review before transmission',
      'tx_transcript': 'Recognized speech',
      'tx_translation': 'Translation to transmit',
      'tx_transmit': 'Transmit over VHF',
      'tx_cancel': 'Discard draft',
      'tx_queued': 'Waiting for Station',
      'tx_queued_body':
          'The translation is ready and waiting for its transmission turn.',
      'tx_transmitting': 'Station is transmitting',
      'tx_transmitting_body':
          'RX is paused while the TX signal is being transmitted.',
      'tx_completed': 'Transmission complete',
      'tx_completed_body': 'The Station released PTT and returned to RX mode.',
      'tx_new_message': 'Create another transmission',
      'tx_station_offline': 'The Station is offline. TX cannot be started.',
      'tx_station_offline_during_tx':
          'Connection to the Station was lost during transmission. The TX result is unconfirmed.',
      'tx_ptt_unavailable':
          'PTT control is unavailable. Check the Station GPIO or configuration.',
      'tx_retry_waiting_station':
          'Wait for the Station to reconnect and confirm failure before retrying.',
      'tx_recording_short': 'RECORDING',
      'tx_release_hint': 'Release to finish',
      'tx_station_busy': 'Another device is currently using this Station.',
      'tx_channel_busy':
          'The VHF channel is busy. The transmission was cancelled.',
      'tx_expired': 'The TX session expired. Please record it again.',
      'tx_processing_failed':
          'The translation could not be prepared. Please try again.',
      'tx_audio_too_long':
          'The recording exceeds the allowed duration. Please record it again.',
      'tx_output_too_long':
          'The translated audio exceeds 120 seconds. Shorten the text and try again.',
      'tx_synthesis_timeout':
          'TX audio synthesis timed out. The job stopped safely; retry manually.',
      'tx_playback_timeout':
          'TX playback timed out. PTT was released safely; check the Station.',
      'tx_transmission_failed':
          'The Station could not transmit the translation.',
      'tx_discard_title': 'Discard the current TX draft?',
      'tx_discard_body':
          'The untransmitted recording or translation will be deleted.',
      'tx_discard': 'Discard and leave',
    },
  };

  static String of(BuildContext context, String key) {
    final code = Localizations.localeOf(context).languageCode;
    return _values[code]?[key] ?? _values['vi']![key] ?? key;
  }

  static String format(
    BuildContext context,
    String key,
    Map<String, Object> values,
  ) {
    var result = of(context, key);
    for (final entry in values.entries) {
      result = result.replaceAll('{${entry.key}}', '${entry.value}');
    }
    return result;
  }

  static Locale resolve(Locale? locale, Iterable<Locale> supported) {
    final code =
        locale?.languageCode ?? PlatformDispatcher.instance.locale.languageCode;
    return supported.firstWhere(
      (item) => item.languageCode == code,
      orElse: () => const Locale('vi'),
    );
  }
}
