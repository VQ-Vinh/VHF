# PRANA ELEX

PRANA ELEX là hệ thống thu âm VHF, nhận diện giọng nói và dịch gần thời gian thực.
Dự án hỗ trợ:

- Windows 10/11: ứng dụng desktop và Station dùng WASAPI.
- Raspberry Pi 4B: Station headless dùng PulseAudio.
- Android: ứng dụng Flutter để ghép nối, điều khiển Station và xem kết quả.
- Cloud: FastAPI, Firebase/Firestore, Gemini và Cloud Storage.

Client chỉ thu âm, chạy VAD và gọi PRANA API. Credential Google Cloud, prompt và
cấu hình Gemini chỉ nằm ở backend.

## Cấu trúc

```text
apps/windows/          Ứng dụng Windows và bộ cài
apps/linux/            Station cho Raspberry Pi
apps/android/          Ứng dụng Flutter Android
packages/prana_core/   Pipeline, VAD và station protocol dùng chung
services/prana_api/    Public FastAPI service
services/prana_admin/  Trang quản trị được bảo vệ bằng IAP
infra/                 Terraform và Firestore Rules
tests/                 Test Python theo từng subsystem
```

Xem thêm [kiến trúc hệ thống](docs/architecture.md) và
[sơ đồ tổng quan](docs/architecture-overview.md).

## Yêu cầu

- Python 3.11 trở lên
- Windows 10/11 x64 hoặc Raspberry Pi OS Bookworm ARM64
- Flutter SDK và Android SDK nếu phát triển ứng dụng Android

## Chạy từ source

### Windows

```bat
scripts\setup\setup.bat
run_dev.bat
```

Chạy Station, API local, Android Emulator và Flutter staging:

```bat
enable_station.bat
```

Chạy API riêng:

```bat
run_api.bat
```

### Raspberry Pi/Linux

```bash
./scripts/setup/setup.sh
./apps/linux/run.sh
```

### Android

Tạo file cấu hình từ `apps/android/config/staging.example.json`, sau đó:

```bat
run_mobile.bat
```

## Test

Windows PowerShell:

```powershell
$env:PYTHONPATH="packages/prana_core/src;apps/windows/src;apps/linux/src;."
.venv\dev\Scripts\python.exe -m pytest tests/core tests/windows tests/linux tests/packaging
.venv\backend\Scripts\python.exe -m pytest tests/api tests/admin
cd apps/android
flutter test
```

## Build

Chạy lệnh tương ứng từ thư mục gốc:

```bat
buildwin.bat
buildapp.bat
```

Trên Raspberry Pi:

```bash
./buildlinux
```

Artifact được tạo trong:

```text
installers/windows/
installers/android/
installers/linux/
```

Android production cần cấu hình keystore. Windows release cần Inno Setup; Linux
release phải được build trực tiếp trên Raspberry Pi ARM64.

## Cấu hình và bảo mật

Config client nằm tại:

- `apps/windows/config/default.toml`
- `apps/linux/config/default.toml`
- `apps/android/config/*.example.json`

Không commit service-account JSON, private key, token, signing key hoặc credential.
Firebase Web API key và OAuth client ID trong client chỉ là định danh public; mọi
quyền nghiệp vụ vẫn được kiểm tra tại API.

Hướng dẫn staging đầy đủ: [docs/staging-e2e-test-guide.md](docs/staging-e2e-test-guide.md).
