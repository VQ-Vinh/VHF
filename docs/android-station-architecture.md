# Kiến trúc Android và Station

## Tổng quan

PRANA ELEX gồm bốn vùng chạy độc lập:

```text
Android App ── Firebase ID token ──> PRANA API ── IAM ──> Firestore/GCS/Gemini
     │                                  ▲
     │ Firestore read-only projection   │ Ed25519 signed requests
     ▼                                  │
users/{uid}/stations/...             Station Windows/Linux/Pi

Web Admin ── IAP + allowlist ──> Admin service ── IAM ──> Firestore
```

- Android là client đăng nhập của người dùng, dùng Firebase Authentication.
- Station không giữ Firebase token; mỗi Station có khóa Ed25519 độc lập.
- PRANA API là đường ghi duy nhất cho Android và Station.
- Android chỉ đọc projection Station của chính chủ sở hữu.
- Web Admin là dịch vụ riêng, được bảo vệ bởi IAP, allowlist và CSRF.

## Android App

### Điều hướng và trạng thái

`GoRouter` chuyển người chưa đăng nhập tới `/sign-in`. Người đã đăng nhập có
các route Station list, pairing/activation, Live, History, Station settings và
Account Center.

Riverpod quản lý các nguồn trạng thái chính:

- Firebase auth state và ID token.
- Danh sách/projection Station từ Firestore.
- Đồng hồ 5 giây để tính online/offline.
- API health, account, plan entitlement và Live results.
- Controller lạc quan cho Start/Stop, ngôn ngữ và Retry.
- Ngôn ngữ giao diện VI/EN được lưu trong secure storage.

Android coi Station offline nếu `last_seen_at` cũ hơn 15 giây. Desired state
được hiển thị ở trạng thái chờ cho đến khi `observed_generation` bắt kịp
`desired_generation`.

### Xác thực và tài khoản

App hỗ trợ Email/Password, Google, xác minh email, gửi lại email xác minh, quên
mật khẩu và liên kết Google vào tài khoản hiện có. Firebase ID token được gắn
vào mọi request người dùng tới PRANA API.

Account Center tổng hợp account, quota ngày, plan catalog, devices và Stations.
Người dùng chỉ tự chọn plan có `availability=available`; Plus/Pro không thể
chọn nếu backend chưa phát hành. Revoke device/Station luôn yêu cầu xác nhận.

### Pairing và activation

Luồng nhãn thiết bị cố định:

1. `prana-station-provision` đăng ký public key và activation hash.
2. Nhãn QR chứa Setup ID 10 ký tự và activation code 16 ký tự, không chứa
   private key.
3. Android gọi `POST /v1/station-activations/claim`.
4. Claim đầu tiên gán owner; cùng owner scan lại là idempotent; owner khác,
   mã sai, Station revoke hoặc vượt `max_stations` bị từ chối.

Luồng pairing tạm thời vẫn được giữ để tương thích:

1. Station chứng minh private key với `POST /v1/station-pairings`.
2. API trả code dùng một lần, hết hạn sau 10 phút.
3. Android nhận deep link `prana-elex:///pair` hoặc nhập code.
4. Transaction kiểm tra code, owner và giới hạn Station của plan.

Activation code không dùng để chuyển chủ. Transfer chỉ thực hiện trong Web
Admin và phải được audit.

## Điều khiển và xử lý bản dịch

Station poll desired state mỗi 2 giây, heartbeat mỗi 5 giây. Generation counter
giúp Start, Stop, thay ngôn ngữ và cấu hình audio latest-wins, idempotent. Retry
có counter riêng. Heartbeat chứa capture state, session, sequence, observed
generation, platform, app version, audio device và lỗi/retry.

Station gửi WAV bằng request ký Ed25519. API xác định owner từ
`station_registry`, sau đó áp dụng:

- kiểm tra chữ ký, timestamp, nonce và idempotency;
- validation WAV và giới hạn segment;
- quota ngày, concurrency và circuit breaker toàn hệ thống;
- xử lý Gemini, lưu archive GCS và ghi result projection;
- TTL 14 ngày cho kết quả; projection không chứa audio URL.

Live App poll endpoint result theo session mỗi 2 giây. `live_log_limit=0` nghĩa
là không giới hạn theo entitlement; giá trị dương giới hạn số log gần nhất.
Trước khi render, App đổi timestamp sang múi giờ điện thoại và chỉ giữ log thuộc
ngày hiện tại. Khi qua 00:00, vòng poll kế tiếp tự loại log ngày hôm trước.

## History theo ngày

History không hiển thị session ID. API tổng hợp result của mọi session theo
timestamp và múi giờ do điện thoại gửi:

- `GET /v1/stations/{id}/history/days` trả mỗi ngày một mục, số log, thời gian
  đầu/cuối và trạng thái khóa.
- `GET /v1/stations/{id}/history/days/{date}/results` trả toàn bộ ngày bằng
  cursor pagination.
- Session đi qua nửa đêm được chia theo timestamp của từng result.
- `history_unlock_delay_days=1` hiển thị ngày hiện tại nhưng khóa và mở từ
  00:00 ngày hôm sau; `0` cho phép xem ngay.

Android loại trùng theo `request_id`, sắp xếp ổn định theo timestamp, sequence
và request ID. Search, ẩn tạm khỏi màn hình và export TXT/CSV áp dụng trên toàn
bộ ngày; file có dạng `prana-YYYY-MM-DD.txt|csv`.

## Dữ liệu và ranh giới tin cậy

Private collections gồm `station_registry`, `station_pairings`,
`station_activation_index`, attempt/rate-limit collections và
`station_request_nonces`. Projection người dùng:

```text
users/{uid}/stations/{station_id}
users/{uid}/stations/{station_id}/sessions/{session_id}
users/{uid}/stations/{station_id}/sessions/{session_id}/results/{request_id}
```

Firestore Rules chỉ cho owner đọc projection Station và chặn mọi client write.
History/Live result được trả qua PRANA API để backend thực thi entitlement.
Admin SDK dùng IAM và không phụ thuộc Firestore Rules.

## Web Admin và vận hành

Web Admin có Dashboard, Users, Plans, Stations và Audit log:

- IAP xác thực operator; production fail-closed nếu allowlist rỗng.
- Mọi POST form dùng signed double-submit CSRF token gắn với operator.
- Mutation và audit nằm trong cùng Firestore transaction/batch.
- Audit lưu operator, action, target, before/after, request ID và timestamp.
- Plan mặc định chỉ đọc; icon bút chì mở chỉnh sửa, Save chỉ bật khi form hợp
  lệ và có thay đổi.
- Station detail hiển thị runtime/generation; Stop gửi desired state. Transfer
  yêu cầu Station idle, kiểm tra `max_stations` từ collection `plans` và xác
  nhận lại email owner mới.

Cloud Run giữ stateless. CSRF signing secret nằm trong Secret Manager. Firestore
giữ desired state, replay/idempotency, pairing, audit và indexes phục vụ bộ lọc.

## Triển khai và tài liệu kiểm thử

- Generate label từ máy Windows tại thư mục dự án:
  `generate_station_qr.bat`. PNG/SVG được lưu trong `stations/`.
- Provision trực tiếp trên Pi:
  `prana-station-provision --config apps/linux/config/default.toml --output ~/prana-station-label`
- Chạy Station:
  `prana-station --config apps/linux/config/default.toml`
- Bootstrap plan sau deploy để luôn có `max_stations`, Live limit và History
  delay.
- Deploy Rules, TTL và composite indexes bằng Terraform.
- Kịch bản QA Android + Web Admin:
  [android-web-admin-test-scenarios.md](android-web-admin-test-scenarios.md).
- Hướng dẫn E2E Windows/staging:
  [staging-e2e-test-guide.md](staging-e2e-test-guide.md).
