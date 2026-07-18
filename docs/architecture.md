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
                   ├─ subscription, device, quota và idempotency trong Firestore
                   ├─ Gemini qua Vertex AI bằng Cloud Run service identity
                   └─ WAV/result trên Cloud Storage với lifecycle 14 ngày

PRANA Admin (Cloud Run + IAP)
  └─ quản lý user, plan, subscription, device và audit trong Firestore
```

Client không chứa Google service-account JSON và không gọi Vertex AI hoặc Cloud Storage trực tiếp. Firebase Web API key trong build profile là định danh public; quyền truy cập nghiệp vụ luôn yêu cầu Firebase ID token và device signature.

## Ranh giới mã nguồn

- `src/prana_elex`: client dùng chung cho Windows và Raspberry Pi.
  - `ui`: application shell, account controller và các page Qt.
  - `pipeline`: lifecycle recorder/VAD/worker; `SegmentProcessor` xử lý từng segment.
  - `backend`: Firebase auth, secure store, device identity và REST client.
  - `audio`, `vad`, `storage`, `config`: adapter theo nền tảng và dữ liệu local.
- `services/prana_api`: FastAPI nghiệp vụ và adapter Google Cloud.
- `services/prana_admin`: web quản trị được bảo vệ bằng IAP.
- `infra`: Firebase rules và Terraform production/staging.
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
