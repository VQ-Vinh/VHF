from __future__ import annotations

from PySide6.QtCore import QObject, Signal


_CATALOGS: dict[str, dict[str, str]] = {
    "en": {
        "app.subtitle": "MARINE VHF",
        "common.english": "English",
        "common.vietnamese": "Tiếng Việt",
        "common.save": "Save",
        "common.cancel": "Cancel",
        "common.refresh": "Refresh",
        "common.sign_out": "Sign Out",
        "common.retry": "Retry",
        "common.status": "Status",
        "header.start": "Start",
        "header.stop": "Stop",
        "header.starting": "Starting…",
        "header.stopping": "Stopping…",
        "header.settings": "Settings",
        "header.rx_off": "RX OFF",
        "header.rx_starting": "RX STARTING",
        "header.rx_active": "RX ACTIVE",
        "header.rx_receiving": "RX RECEIVING",
        "header.rx_error": "RX ERROR",
        "language.input": "INPUT LANGUAGE",
        "language.output": "OUTPUT LANGUAGE",
        "language.detecting": "Detecting…",
        "feed.title": "LIVE TRANSLATION",
        "feed.empty_title": "Ready to translate",
        "feed.empty_body": "Press Start to begin receiving and translating VHF audio.",
        "feed.history": "Translation history",
        "feed.idle": "IDLE",
        "feed.listening": "LISTENING",
        "feed.receiving": "RECEIVING",
        "feed.error": "ERROR",
        "feed.starting": "STARTING",
        "feed.stopping": "STOPPING",
        "feed.latency": "LATENCY",
        "feed.api_off": "API OFF",
        "feed.api_ready": "API READY",
        "feed.api_ok": "API OK",
        "feed.api_error": "API ERROR",
        "account.welcome": "Welcome to PRANA ELEX",
        "account.subtitle": "Sign in to use your PRANA ELEX subscription.",
        "account.sign_in": "Sign In",
        "account.create": "Create Account",
        "account.email": "Email",
        "account.password": "Password",
        "account.show_password": "Show password",
        "account.forgot": "Forgot Password",
        "account.checking": "Checking your account…",
        "account.status": "Account status",
        "account.resend": "Resend Verification",
        "account.invalid": "Enter a valid email and a password of at least 6 characters.",
        "account.signing_in": "Signing in…",
        "account.data_title": "Choose a Data folder",
        "account.data_body": "Recordings and translation results are stored locally in this folder.",
        "account.browse": "Browse…",
        "account.offline": "Connection unavailable",
        "account.offline_body": "PRANA ELEX could not reach the service. Your session is still saved.",
        "settings.title": "Settings",
        "settings.audio": "Audio capture",
        "settings.account": "Account",
        "settings.language": "Interface language",
        "settings.capture_mode": "Capture mode",
        "settings.device": "Device",
        "settings.autostart": "Start PRANA ELEX when I log in",
        "settings.subscription": "Subscription",
        "settings.expires": "Expires",
        "settings.usage": "Monthly usage",
        "settings.devices": "Devices",
        "settings.revoke": "Revoke",
        "history.title": "Translation History",
        "history.search": "Search transcripts and translations…",
        "history.export": "Export",
        "history.clear": "Clear All",
        "history.time": "Time",
        "history.language": "Language",
        "history.transcript": "Transcript",
        "history.translation": "Translation",
        "console.title": "Developer Console",
        "console.retry": "Retry Failed Audio",
        "tray.show": "Show/Hide",
        "tray.exit": "Exit",
    },
    "vi": {
        "app.subtitle": "BỘ ĐÀM HÀNG HẢI VHF",
        "common.english": "English",
        "common.vietnamese": "Tiếng Việt",
        "common.save": "Lưu",
        "common.cancel": "Hủy",
        "common.refresh": "Làm mới",
        "common.sign_out": "Đăng xuất",
        "common.retry": "Thử lại",
        "common.status": "Trạng thái",
        "header.start": "Bắt đầu",
        "header.stop": "Dừng",
        "header.starting": "Đang khởi động…",
        "header.stopping": "Đang dừng…",
        "header.settings": "Cài đặt",
        "header.rx_off": "RX ĐÃ TẮT",
        "header.rx_starting": "RX ĐANG KHỞI ĐỘNG",
        "header.rx_active": "RX ĐANG HOẠT ĐỘNG",
        "header.rx_receiving": "RX ĐANG NHẬN",
        "header.rx_error": "RX LỖI",
        "language.input": "NGÔN NGỮ ĐẦU VÀO",
        "language.output": "NGÔN NGỮ ĐẦU RA",
        "language.detecting": "Đang nhận diện…",
        "feed.title": "BẢN DỊCH TRỰC TIẾP",
        "feed.empty_title": "Sẵn sàng dịch",
        "feed.empty_body": "Nhấn Bắt đầu để nhận và dịch âm thanh VHF.",
        "feed.history": "Lịch sử bản dịch",
        "feed.idle": "CHỜ",
        "feed.listening": "ĐANG NGHE",
        "feed.receiving": "ĐANG NHẬN",
        "feed.error": "LỖI",
        "feed.starting": "ĐANG KHỞI ĐỘNG",
        "feed.stopping": "ĐANG DỪNG",
        "feed.latency": "ĐỘ TRỄ",
        "feed.api_off": "API TẮT",
        "feed.api_ready": "API SẴN SÀNG",
        "feed.api_ok": "API TỐT",
        "feed.api_error": "API LỖI",
        "account.welcome": "Chào mừng đến với PRANA ELEX",
        "account.subtitle": "Đăng nhập để sử dụng gói dịch vụ PRANA ELEX.",
        "account.sign_in": "Đăng nhập",
        "account.create": "Tạo tài khoản",
        "account.email": "Email",
        "account.password": "Mật khẩu",
        "account.show_password": "Hiện mật khẩu",
        "account.forgot": "Quên mật khẩu",
        "account.checking": "Đang kiểm tra tài khoản…",
        "account.status": "Trạng thái tài khoản",
        "account.resend": "Gửi lại email xác minh",
        "account.invalid": "Nhập email hợp lệ và mật khẩu có ít nhất 6 ký tự.",
        "account.signing_in": "Đang đăng nhập…",
        "account.data_title": "Chọn thư mục dữ liệu",
        "account.data_body": "Bản ghi và kết quả dịch được lưu cục bộ trong thư mục này.",
        "account.browse": "Chọn…",
        "account.offline": "Không thể kết nối",
        "account.offline_body": "PRANA ELEX không thể kết nối dịch vụ. Phiên đăng nhập vẫn được giữ.",
        "settings.title": "Cài đặt",
        "settings.audio": "Thu âm",
        "settings.account": "Tài khoản",
        "settings.language": "Ngôn ngữ giao diện",
        "settings.capture_mode": "Chế độ thu",
        "settings.device": "Thiết bị",
        "settings.autostart": "Khởi động PRANA ELEX khi đăng nhập máy",
        "settings.subscription": "Gói dịch vụ",
        "settings.expires": "Hết hạn",
        "settings.usage": "Sử dụng tháng",
        "settings.devices": "Thiết bị",
        "settings.revoke": "Thu hồi",
        "history.title": "Lịch sử bản dịch",
        "history.search": "Tìm trong nội dung và bản dịch…",
        "history.export": "Xuất file",
        "history.clear": "Xóa tất cả",
        "history.time": "Thời gian",
        "history.language": "Ngôn ngữ",
        "history.transcript": "Nội dung gốc",
        "history.translation": "Bản dịch",
        "console.title": "Bảng điều khiển kỹ thuật",
        "console.retry": "Thử lại âm thanh lỗi",
        "tray.show": "Hiện/Ẩn",
        "tray.exit": "Thoát",
    },
}


class LanguageManager(QObject):
    changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._locale = "en"

    @property
    def locale(self) -> str:
        return self._locale

    def set_locale(self, locale: str) -> None:
        locale = locale if locale in _CATALOGS else "en"
        if locale == self._locale:
            return
        self._locale = locale
        self.changed.emit(locale)

    def text(self, key: str, **params: object) -> str:
        value = _CATALOGS.get(self._locale, _CATALOGS["en"]).get(key)
        if value is None:
            value = _CATALOGS["en"].get(key, key)
        return value.format(**params) if params else value


language = LanguageManager()


def tr(key: str, **params: object) -> str:
    return language.text(key, **params)
