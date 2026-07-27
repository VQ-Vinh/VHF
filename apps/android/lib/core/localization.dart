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
      'waiting': 'Đang chờ trạm',
      'history': 'Lịch sử',
      'input': 'Đầu vào',
      'output': 'Đầu ra',
      'detecting': 'Đang phát hiện',
      'translations': 'Bản dịch trực tiếp',
      'empty_title': 'Đang chờ tín hiệu thoại',
      'empty_body': 'Bắt đầu thu để nhận transcript và bản dịch.',
      'diagnostics': 'Chẩn đoán trạm',
      'retry': 'Thử lại',
      'offline': 'Offline quá 15 giây',
      'api_ready': 'API READY',
      'api_error': 'API ERROR',
      'quota_near': 'Bạn sắp sử dụng hết thời lượng của gói.',
      'quota_exhausted': 'Đã sử dụng hết thời lượng của gói.',
      'settings': 'Cài đặt',
      'ui_language': 'Ngôn ngữ giao diện',
      'stations': 'Trạm của tôi',
      'account': 'Tài khoản',
      'pair_station': 'Ghép trạm',
      'no_station': 'Chưa có trạm',
      'no_station_body':
          'Quét tem QR trên thiết bị hoặc dùng mã tạm thời để ghép trạm.',
      'sign_in': 'Đăng nhập',
      'signing_in': 'Đang xử lý...',
      'password': 'Mật khẩu',
      'google': 'Tiếp tục với Google',
      'create_account': 'Tạo tài khoản',
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
      'session': 'Phiên',
      'not_started': 'chưa bắt đầu',
      'no_sessions': 'Chưa có phiên dịch nào',
      'no_sessions_body': 'Các phiên hoàn tất sẽ xuất hiện tại đây.',
      'syncing': 'Đang đồng bộ',
      'connect_station': 'Kết nối PRANA Station',
      'label_help':
          'Quét tem QR cố định được dán trên Raspberry Pi hoặc Laptop.',
      'temporary_help': 'Dùng mã tạm thời do Laptop hoặc station cũ tạo ra.',
      'activation_help': '16 ký tự, tự động chia thành 4 nhóm',
      'station_missing': 'Trạm không còn tồn tại',
      'realtime_error': 'Mất kết nối realtime',
      'history_mode':
          'Đang xem lịch sử. Điều khiển vẫn áp dụng cho trạm hiện tại.',
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
      'clear_view': 'Xóa khỏi màn hình',
      'forgot_password': 'Quên mật khẩu',
      'reset_password': 'Gửi email đặt lại mật khẩu',
      'reset_sent': 'Đã gửi email đặt lại mật khẩu nếu tài khoản tồn tại.',
      'linked': 'Đã liên kết',
      'not_linked': 'Chưa liên kết',
      'link_google': 'Liên kết Google',
      'usage': 'Mức sử dụng',
      'plans': 'Gói dịch vụ',
      'devices': 'Thiết bị và trạm',
      'confirm_revoke': 'Xác nhận thu hồi',
      'revoke': 'Thu hồi',
      'done': 'Đã hoàn tất',
      'live_log_usage': 'Đang hiển thị {count}/{limit} log theo gói',
      'history_restricted':
          'Kết quả mới được giới hạn theo gói. Toàn bộ lịch sử sẽ mở khóa sau {days} ngày.',
      'error_connection_timeout':
          'Không thể kết nối PRANA API. Nếu dùng điện thoại thật, hãy kiểm tra API_URL không còn là 10.0.2.2.',
      'error_request_timeout': 'PRANA API phản hồi quá chậm. Hãy thử lại.',
      'error_api_unreachable':
          'Không thể truy cập PRANA API. Kiểm tra mạng và địa chỉ máy chủ.',
      'error_request_failed': 'Không thể thực hiện yêu cầu. Hãy thử lại.',
      'processing_retrying': 'Máy chủ đang bận, đang thử lại ({attempt}/3)…',
    },
    'en': {
      'start': 'Start',
      'stop': 'Stop',
      'waiting': 'Waiting for station',
      'history': 'History',
      'input': 'Input',
      'output': 'Output',
      'detecting': 'Detecting',
      'translations': 'Live translations',
      'empty_title': 'Waiting for speech',
      'empty_body': 'Start capture to receive transcript and translation.',
      'diagnostics': 'Station diagnostics',
      'retry': 'Retry',
      'offline': 'Offline for more than 15 seconds',
      'api_ready': 'API READY',
      'api_error': 'API ERROR',
      'quota_near': 'You are nearing your plan usage limit.',
      'quota_exhausted': 'Your plan usage limit has been reached.',
      'settings': 'Settings',
      'ui_language': 'Interface language',
      'stations': 'My stations',
      'account': 'Account',
      'pair_station': 'Pair station',
      'no_station': 'No stations yet',
      'no_station_body':
          'Scan the device QR label or use a temporary pairing code.',
      'sign_in': 'Sign in',
      'signing_in': 'Working...',
      'password': 'Password',
      'google': 'Continue with Google',
      'create_account': 'Create account',
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
      'session': 'Session',
      'not_started': 'not started',
      'no_sessions': 'No translation sessions yet',
      'no_sessions_body': 'Completed sessions will appear here.',
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
      'history_mode':
          'Viewing history. Controls still apply to the current station.',
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
      'clear_view': 'Clear from view',
      'forgot_password': 'Forgot password',
      'reset_password': 'Send password reset email',
      'reset_sent': 'A password reset email was sent if the account exists.',
      'linked': 'Linked',
      'not_linked': 'Not linked',
      'link_google': 'Link Google',
      'usage': 'Usage',
      'plans': 'Plans',
      'devices': 'Devices and stations',
      'confirm_revoke': 'Confirm revoke',
      'revoke': 'Revoke',
      'done': 'Completed',
      'live_log_usage': 'Showing {count}/{limit} plan logs',
      'history_restricted':
          'Recent results are limited by your plan. Full history unlocks after {days} day(s).',
      'error_connection_timeout':
          'Cannot connect to PRANA API. On a physical phone, make sure API_URL is not 10.0.2.2.',
      'error_request_timeout': 'PRANA API took too long to respond. Try again.',
      'error_api_unreachable':
          'PRANA API is unreachable. Check the network and server address.',
      'error_request_failed': 'The request could not be completed. Try again.',
      'processing_retrying': 'The server is busy, retrying ({attempt}/3)…',
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
