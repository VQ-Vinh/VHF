# Kịch bản kiểm thử Android App và Web Admin

## 1. Mục tiêu và chuẩn bị

Tài liệu này là checklist nghiệm thu đầy đủ cho Android, Station và Web Admin
trên staging. Không dùng tài khoản hoặc audio thật của khách hàng.

Chuẩn bị:

- Một Android 10+ và một thiết bị có múi giờ có thể thay đổi.
- Một Station provisioned, một Station pairing tạm thời và nguồn audio EN/VI.
- Hai user đã xác minh (`user-a`, `user-b`), một user chưa xác minh, một Admin
  trong IAP/allowlist và một Google account không có quyền Admin.
- Plan Free (`live_log_limit > 0`, History delay 1), một plan delay 0 và dữ liệu
  hơn 1.000 results trên nhiều session trong cùng ngày.
- Ghi lại app build, API/Admin revision, Station version và thời gian test.

Mỗi case lưu `PASS/FAIL/BLOCKED`, ảnh màn hình, timestamp, account/Station ID
đã che bớt và request ID nếu có. Không lưu token, activation code, private key
hoặc CSRF secret.

## 2. Android — xác thực và nền tảng

| ID | Kịch bản | Bước chính | Kết quả mong đợi |
|---|---|---|---|
| AND-AUTH-01 | Điều hướng chưa đăng nhập | Xóa app data, mở deep link Live/History | Luôn chuyển tới Sign in; không lộ dữ liệu |
| AND-AUTH-02 | Đăng ký Email/Password | Thử email sai, mật khẩu yếu, sau đó dữ liệu hợp lệ | Validation rõ ràng; gửi email xác minh; account được tạo đúng trạng thái |
| AND-AUTH-03 | Xác minh email | Đăng nhập trước và sau khi bấm link xác minh | Trước xác minh bị chặn nghiệp vụ; sau xác minh nhận Free và dùng App |
| AND-AUTH-04 | Google sign-in | Đăng nhập Google mới và Google đã liên kết | Tạo/nhận đúng Firebase user, không tạo account trùng |
| AND-AUTH-05 | Liên kết Google | Từ account Email/Password liên kết cùng email; thử email khác | Cùng email liên kết thành công; email khác bị từ chối |
| AND-AUTH-06 | Quên/đổi mật khẩu | Gửi reset, dùng link, đăng nhập mật khẩu mới | Email được gửi; mật khẩu cũ vô hiệu; mật khẩu mới hoạt động |
| AND-AUTH-07 | Session và logout | Kill/reopen App, sau đó logout | Login được nhớ an toàn; logout xóa phiên và route trở về Sign in |
| AND-UI-01 | VI/EN và persistence | Đổi ngôn ngữ, đóng/mở App | Toàn bộ màn hình chính đổi ngôn ngữ và giữ lựa chọn |
| AND-UI-02 | Accessibility/responsive | Font lớn, TalkBack, portrait/landscape, màn 360dp | Không tràn; control có label; focus và thứ tự đọc hợp lý |
| AND-NET-01 | API/Firebase mất mạng | Tắt mạng khi mở list, Live và mutation | Hiển thị offline/error; không crash; phục hồi/poll lại khi có mạng |

## 3. Android — Station và pairing

| ID | Kịch bản | Bước chính | Kết quả mong đợi |
|---|---|---|---|
| AND-PAIR-01 | Activation QR cố định | Scan nhãn hợp lệ và xác nhận claim | Station xuất hiện đúng owner; QR không chứa private key |
| AND-PAIR-02 | Activation idempotent | Cùng user scan lại nhãn | Không tạo Station trùng; trả cùng Station |
| AND-PAIR-03 | Activation lỗi | Nhập code sai, Setup ID sai, Station revoked | Bị từ chối với thông báo an toàn; không đổi owner |
| AND-PAIR-04 | Cross-owner | `user-b` scan Station của `user-a` | Bị từ chối; projection hai user không bị thay đổi |
| AND-PAIR-05 | Giới hạn Station | Claim khi đã đạt `max_stations` | API từ chối đúng entitlement; Station cũ không ảnh hưởng |
| AND-PAIR-06 | Pairing tạm thời | Scan deep link/nhập code 8 ký tự | Claim thành công trong 10 phút; code chỉ dùng một lần |
| AND-PAIR-07 | Pairing hết hạn/replay | Dùng code hết hạn, sai hoặc đã dùng | Bị từ chối; không tạo projection; rate limit hoạt động |
| AND-LIST-01 | Danh sách Station | Có online, offline, lỗi và nhiều Station | Sắp xếp/nhãn đúng; offline sau 15 giây; mở đúng Station |
| AND-LIST-02 | Projection isolation | Đăng nhập `user-b`, thử ID/deep link của `user-a` | Không đọc được projection hoặc result của user khác |

## 4. Android — Live, điều khiển và audio

| ID | Kịch bản | Bước chính | Kết quả mong đợi |
|---|---|---|---|
| AND-LIVE-01 | Start/Stop | Start, quan sát pending/observed; sau đó Stop | Generation tăng; nút chờ tới khi Station ack; capture state đúng |
| AND-LIVE-02 | Latest-wins | Gửi liên tiếp Start/Stop/ngôn ngữ | Station áp dụng generation mới nhất, không lùi trạng thái |
| AND-LIVE-03 | Ngôn ngữ | Đổi target language khi online và khi API lỗi | Optimistic khi gửi; rollback rõ ràng nếu thất bại |
| AND-LIVE-04 | Retry | Tạo processing error rồi bấm Retry | Retry counter tăng; banner tiến trình đúng; không nhầm command failure |
| AND-LIVE-05 | Station offline | Ngắt Station hơn 15 giây | OFFLINE; mutation bị vô hiệu; log đã có không làm App crash |
| AND-LIVE-06 | Dịch EN/VI | Phát audio rõ dưới 15 giây theo hai chiều | Transcript restored, translation, language, timestamp đúng |
| AND-LIVE-07 | WAV/segment lỗi | Im lặng, codec sai, audio quá dài/nhiễu | Lỗi phù hợp; quota/concurrency được hoàn lại khi xử lý thất bại |
| AND-LIVE-08 | Idempotency | Retry cùng request; đổi payload với cùng request ID | Cùng payload trả cache; payload khác trả conflict; không trừ quota hai lần |
| AND-LIVE-09 | Live entitlement | Tạo log vượt `live_log_limit`; thử plan limit 0 | Plan hữu hạn chỉ hiện giới hạn; 0 không áp giới hạn entitlement |
| AND-LIVE-10 | Chỉ log hôm nay | Session chứa 23:59 hôm trước và 00:00 hôm nay | Live chỉ hiện log có ngày địa phương hôm nay |
| AND-LIVE-11 | Qua nửa đêm | Giữ Live mở qua 00:00 hoặc đổi clock test | Poll kế tiếp loại log hôm trước, không cần restart |
| AND-LIVE-12 | Quota | Dùng gần 90%, đạt 100%, chờ reset ngày | Banner cảnh báo; hết quota bị chặn; reset đúng kỳ |
| AND-SET-01 | Capabilities/audio device | Scan device, đổi capture mode/device và Save | Chỉ option được Station hỗ trợ; desired/observed đồng bộ |
| AND-SET-02 | Dirty/pending settings | Không đổi, đổi rồi hoàn tác, gửi khi command pending | Save chỉ bật khi dirty/hợp lệ; pending chống gửi trùng |

## 5. Android — History và Account Center

| ID | Kịch bản | Bước chính | Kết quả mong đợi |
|---|---|---|---|
| AND-HIS-01 | Gộp nhiều session | Tạo nhiều session cùng ngày | Chỉ một thẻ `Ngày dd/MM/yyyy`, không lộ session ID |
| AND-HIS-02 | Qua nửa đêm/múi giờ | Session có result hai phía 00:00; đổi timezone | Result vào đúng ngày địa phương và range đúng |
| AND-HIS-03 | Khóa ngày | Free delay 1 và plan delay 0 | Free thấy thẻ khóa tới 00:00 hôm sau; delay 0 mở ngay |
| AND-HIS-04 | Pagination lớn | Mở ngày có hơn 1.000 results | Tải đủ mọi trang, không thiếu/trùng, thứ tự ổn định |
| AND-HIS-05 | Search/ẩn | Tìm transcript/translation, ẩn một result | Search trên toàn ngày; ẩn chỉ tác động UI hiện tại |
| AND-HIS-06 | Export | Export TXT và CSV một ngày | Tên `prana-YYYY-MM-DD`; đủ log, escape CSV và Unicode đúng |
| AND-HIS-07 | TTL | Kiểm tra result sát và quá 14 ngày | Dữ liệu trong TTL xem được; dữ liệu hết TTL được dọn |
| AND-ACC-01 | Account/quota/plans | Mở Account Center và refresh | Email/status/plan/usage đúng backend; coming-soon bị vô hiệu |
| AND-ACC-02 | Device revoke | Xác nhận revoke device hiện tại/khác | Hủy dialog không đổi; xác nhận revoke đúng device |
| AND-ACC-03 | Station revoke | Revoke Station từ Account Center | Station bị vô hiệu và biến khỏi luồng điều khiển; owner khác không ảnh hưởng |

## 6. Web Admin

| ID | Kịch bản | Bước chính | Kết quả mong đợi |
|---|---|---|---|
| ADM-SEC-01 | IAP và allowlist | Truy cập bằng Admin, account ngoài allowlist và chưa đăng nhập | Admin vào được; hai trường hợp còn lại 403/login; không lộ nội dung |
| ADM-SEC-02 | CSRF | POST thiếu/sai/hết hạn/token operator khác | 403; mutation và audit không được ghi |
| ADM-SEC-03 | Error pages | Gây 403/404/409/422/500 an toàn | Trang VI/EN đúng mã; không hiển thị exception/secret |
| ADM-UI-01 | Locale/responsive | Đổi VI/EN, mobile width, keyboard-only | Cookie locale đúng; nav/dialog/form usable và focus rõ |
| ADM-DASH-01 | Dashboard | Đối chiếu count, Station attention và audit gần nhất | Count đúng aggregation; không stream toàn bộ users |
| ADM-USR-01 | User search/filter/page | Tìm email/UID; lọc status/plan; Next/First | Không thiếu/trùng trong trang; empty state đúng |
| ADM-USR-02 | Suspend/reactivate | Suspend user Plus/Pro rồi activate | Audit nguyên tử; reactivate giữ plan hợp lệ, chỉ Free khi chưa có plan |
| ADM-USR-03 | Reset devices | Reset user tồn tại/không tồn tại | Revoke đúng số device và audit count; user thiếu trả 404 |
| ADM-USR-04 | Re-enrollment | Cho phép một device revoked đăng ký lại | Chỉ target được xóa/re-enroll; audit đúng operator/request |
| ADM-PLAN-01 | Read-only/Edit | Mở Plans, dùng mouse và keyboard bấm bút chì | Mọi input mặc định khóa; chỉ card được chọn mở; ARIA/tooltip đúng |
| ADM-PLAN-02 | Dirty Save/Cancel | Không đổi, đổi, hoàn tác, nhập invalid, Cancel | Save chỉ sáng khi dirty+hợp lệ; hoàn tác tắt Save; Cancel phục hồi |
| ADM-PLAN-03 | Save plan | Sửa limit, xác nhận preview, thử hủy/xác nhận | Hủy không ghi; xác nhận cập nhật ngay và audit before/after nguyên tử |
| ADM-STA-01 | List/filter/search | Lọc online/offline/error/platform; tìm ID/email | Kết quả, last seen, version, capture/error và pagination đúng |
| ADM-STA-02 | Detail/generation | Mở Station detail khi command pending | Desired/observed, audio device, session và transfer history đúng |
| ADM-STA-03 | Stop | Stop Station running và Station idle | Running nhận desired Stop/audit; thao tác idempotent, trạng thái rõ |
| ADM-STA-04 | Transfer idle | Nhập lại target email, transfer sang user còn quota | Registry/projection đổi owner nguyên tử; lịch sử/audit đủ before/after |
| ADM-STA-05 | Transfer bị chặn | Station running, email confirm sai, target đủ quota | Yêu cầu Stop hoặc 409/422 phù hợp; không transfer/audit sai |
| ADM-AUD-01 | Audit filters/page | Lọc operator/action/target/Station/ngày và chuyển trang | Không thiếu/trùng; before/after, request ID, timestamp chính xác |
| ADM-AUD-02 | Transaction rollback | Mô phỏng mutation hoặc audit write thất bại | Cả mutation và audit rollback; trang báo lỗi an toàn |

## 7. Kịch bản xuyên hệ thống và nghiệm thu

| ID | Kịch bản | Kết quả mong đợi |
|---|---|---|
| E2E-01 | Admin đổi `live_log_limit`, App refresh account rồi tạo thêm log | App áp entitlement mới; Live vẫn chỉ hiện ngày hiện tại |
| E2E-02 | Admin đổi History delay 1 → 0 | Sau refresh, ngày hiện tại mở được và đủ log mọi session |
| E2E-03 | Android Start, Admin theo dõi rồi Stop | Generation hội tụ trên Station, Android và Admin; audit chỉ ghi Stop Admin |
| E2E-04 | Admin transfer Station từ A sang B | A mất quyền đọc/điều khiển; B nhận projection sạch và pairing key không đổi |
| E2E-05 | Admin suspend khi Station đang chạy | Request mới bị fail-closed theo entitlement; dữ liệu tenant khác không lộ |
| E2E-06 | Mất API/Firestore rồi phục hồi | Không ghi trùng command/result/audit; UI tự hồi phục hoặc cho retry rõ ràng |

Một test run chỉ được nghiệm thu khi:

- Tất cả case Critical về auth, tenant isolation, CSRF, quota, transfer và
  History lock đều PASS.
- Không còn crash, dữ liệu chéo tenant, mutation không audit hoặc secret xuất
  hiện trong UI/log.
- Android đạt unit/widget tests; API/Admin pytest đạt; Terraform validate và
  smoke test revision staging mới đạt.
- Mọi FAIL còn lại có issue, mức độ ảnh hưởng, owner và quyết định phát hành.
