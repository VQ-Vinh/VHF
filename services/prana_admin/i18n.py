from __future__ import annotations


CATALOGS = {
    "en": {
        "brand.subtitle": "Operations Console",
        "nav.dashboard": "Dashboard", "nav.users": "Users", "nav.plans": "Plans",
        "nav.signed_in": "Signed in as", "nav.language": "Language",
        "dashboard.title": "Operations overview", "dashboard.subtitle": "Customers and service usage at a glance.",
        "dashboard.total": "Total users", "dashboard.active": "Active subscriptions",
        "dashboard.pending": "Awaiting activation", "dashboard.usage": "Audio this month",
        "dashboard.needs_action": "Needs attention", "dashboard.activity": "Recent admin activity",
        "users.title": "Users", "users.subtitle": "Find accounts, review access and manage subscriptions.",
        "users.search": "Search email or UID", "users.status": "All statuses", "users.plan": "All plans",
        "users.filter": "Apply filters", "users.clear": "Clear", "users.user": "User",
        "users.expires": "Expires", "users.empty": "No users match these filters.",
        "users.next": "Next page", "users.first": "First page",
        "user.back": "Back to users", "user.overview": "Account overview",
        "user.subscription": "Subscription", "user.devices": "Devices", "user.usage": "Usage history",
        "user.activate": "Activate or extend", "user.set_status": "Update status",
        "user.revoke_all": "Revoke all devices", "user.allow": "Allow re-enrollment",
        "user.days": "Number of days", "user.period": "UTC period", "user.minutes": "Audio minutes",
        "user.requests": "Requests", "user.no_devices": "No devices registered.",
        "user.no_usage": "No usage recorded.",
        "plans.title": "Plans", "plans.subtitle": "Configure quota and request limits for subscriptions.",
        "plans.create": "Create or update plan", "plans.id": "Plan ID", "plans.name": "Display name",
        "plans.minutes": "Minutes per month", "plans.rpm": "Requests per minute", "plans.save": "Save plan",
        "common.status": "Status", "common.plan": "Plan", "common.actions": "Actions",
        "common.active": "Active", "common.inactive": "Inactive", "common.none": "None",
        "notice.subscription_updated": "Subscription updated successfully.",
        "notice.status_updated": "Account status updated.", "notice.devices_revoked": "All devices were revoked.",
        "notice.device_reenrollment": "The device can now be enrolled again.",
        "notice.plan_saved": "Plan saved successfully.",
    },
    "vi": {
        "brand.subtitle": "Bảng điều hành", "nav.dashboard": "Tổng quan", "nav.users": "Người dùng",
        "nav.plans": "Gói dịch vụ", "nav.signed_in": "Đăng nhập với", "nav.language": "Ngôn ngữ",
        "dashboard.title": "Tổng quan vận hành", "dashboard.subtitle": "Theo dõi khách hàng và mức sử dụng dịch vụ.",
        "dashboard.total": "Tổng người dùng", "dashboard.active": "Gói đang hoạt động",
        "dashboard.pending": "Chờ kích hoạt", "dashboard.usage": "Âm thanh tháng này",
        "dashboard.needs_action": "Cần xử lý", "dashboard.activity": "Hoạt động quản trị gần đây",
        "users.title": "Người dùng", "users.subtitle": "Tìm tài khoản, kiểm tra quyền và quản lý gói dịch vụ.",
        "users.search": "Tìm email hoặc UID", "users.status": "Tất cả trạng thái", "users.plan": "Tất cả gói",
        "users.filter": "Lọc", "users.clear": "Xóa bộ lọc", "users.user": "Người dùng",
        "users.expires": "Hết hạn", "users.empty": "Không có người dùng phù hợp.",
        "users.next": "Trang sau", "users.first": "Trang đầu",
        "user.back": "Quay lại người dùng", "user.overview": "Tổng quan tài khoản",
        "user.subscription": "Gói dịch vụ", "user.devices": "Thiết bị", "user.usage": "Lịch sử sử dụng",
        "user.activate": "Kích hoạt hoặc gia hạn", "user.set_status": "Cập nhật trạng thái",
        "user.revoke_all": "Thu hồi mọi thiết bị", "user.allow": "Cho phép đăng ký lại",
        "user.days": "Số ngày", "user.period": "Kỳ UTC", "user.minutes": "Phút âm thanh",
        "user.requests": "Yêu cầu", "user.no_devices": "Chưa đăng ký thiết bị.",
        "user.no_usage": "Chưa có dữ liệu sử dụng.",
        "plans.title": "Gói dịch vụ", "plans.subtitle": "Cấu hình hạn mức và tần suất yêu cầu.",
        "plans.create": "Tạo hoặc cập nhật gói", "plans.id": "Mã gói", "plans.name": "Tên hiển thị",
        "plans.minutes": "Phút mỗi tháng", "plans.rpm": "Yêu cầu mỗi phút", "plans.save": "Lưu gói",
        "common.status": "Trạng thái", "common.plan": "Gói", "common.actions": "Thao tác",
        "common.active": "Hoạt động", "common.inactive": "Không hoạt động", "common.none": "Không có",
        "notice.subscription_updated": "Đã cập nhật gói dịch vụ.",
        "notice.status_updated": "Đã cập nhật trạng thái tài khoản.",
        "notice.devices_revoked": "Đã thu hồi mọi thiết bị.",
        "notice.device_reenrollment": "Thiết bị có thể đăng ký lại.",
        "notice.plan_saved": "Đã lưu gói dịch vụ.",
    },
}


def translator(locale: str):
    selected = CATALOGS.get(locale, CATALOGS["en"])

    def text(key: str) -> str:
        return selected.get(key, CATALOGS["en"].get(key, key))

    return text
