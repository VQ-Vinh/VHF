# Kiến trúc PRANA ELEX

PRANA ELEX là monorepo gồm ba ứng dụng triển khai độc lập nhưng dùng chung quy trình phát triển.

## Ranh giới hệ thống

```text
Desktop / Raspberry Pi client
  ├─ capture audio, VAD, UI và dữ liệu local trong Data folder đã chọn
  └─ Firebase ID token + chữ ký Ed25519 thiết bị
                         │ HTTPS
                         ▼
                 PRANA API (Cloud Run)
                   ├─ tự cấp Free, quota ngày UTC, device và idempotency trong Firestore
                   ├─ Gemini qua Vertex AI bằng Cloud Run service identity
                   └─ WAV/result trên Cloud Storage với lifecycle 14 ngày

PRANA Admin (Cloud Run + IAP)
  └─ chỉnh hạn mức plan, suspend/reactivate user, quản lý device và audit
```

Client không chứa Google service-account JSON và không gọi Vertex AI hoặc Cloud Storage trực tiếp. Firebase Web API key trong build profile là định danh public; quyền truy cập nghiệp vụ luôn yêu cầu Firebase ID token và device signature.

Tài khoản đã xác minh tự động nhận Free không hết hạn. Catalog Free/Plus/Pro nằm
trong Firestore; Admin có thể chỉnh tên, quota ngày, RPM, concurrency, số thiết bị
và thứ tự hiển thị. Mọi lần sửa đều có audit. Plus và Pro vẫn ở trạng thái
`coming_soon` cho tới khi có luồng thanh toán. Usage của khách hàng được reserve và
settle theo document ngày `YYYY-MM-DD` và reset lúc `00:00 UTC`.

## Ranh giới mã nguồn

- `src/prana_elex`: client dùng chung cho Windows và Raspberry Pi.
  - `ui`: application shell, account controller và các page Qt.
  - `pipeline`: lifecycle recorder/VAD/worker; `SegmentProcessor` xử lý từng segment.
  - `backend`: Firebase auth, Google OAuth PKCE/loopback, secure store, device
    identity và REST client. App gửi code/verifier đến PRANA API; chỉ Firebase refresh
    token được lưu trên thiết bị.
  - `audio`, `vad`, `storage`, `config`: adapter theo nền tảng và dữ liệu local.
- `services/prana_api`: FastAPI nghiệp vụ và adapter Google Cloud.
- `services/prana_admin`: web quản trị được bảo vệ bằng IAP.
- `infra`: Firebase rules và Terraform production/staging.

Google Desktop client secret nằm trong Secret Manager và chỉ Cloud Run runtime đọc.
PRANA API đổi authorization code sang Google token trong bộ nhớ, xác minh email rồi
đổi sang Firebase session. API không log token, không lưu Google token và không trả
Desktop secret cho client.
- `scripts/packaging`: build environment và artifact tách theo platform.

Dependency phải đi theo chiều UI → pipeline/backend → adapter. Service không import client package và client không import code trong `services`.

## Môi trường phát triển

```text
.venv/dev          Client source và test Qt
.venv/backend      API/Admin và test backend
.venv/windows      PyInstaller/Inno Setup Windows
.venv/linux-arm64  PyInstaller/Debian package trên Pi
```

`build`, `dist`, `release`, `.secrets`, Terraform state/values và dữ liệu runtime chỉ tồn tại local, không được commit.
