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
- Windows 10/11 x64 và Google Cloud CLI nếu vận hành Laptop Station
- Raspberry Pi OS Bookworm ARM64 nếu vận hành Pi Station
- Flutter SDK stable 3.44.8+, Android SDK và JDK 17 chỉ khi phát triển hoặc
  build Android

## Bắt đầu nhanh trên Windows

Sau khi clone repository:

```bat
scripts\setup\setup.bat
generate_station_qr.bat
enable_station_api.bat
```

`setup.bat` cài môi trường Station và backend. `generate_station_qr.bat` tạo
nhãn PNG/SVG trong thư mục cục bộ `stations\`; activation code trong nhãn không
được commit hoặc chia sẻ công khai.

Cài APK mới nhất từ [GitHub Releases](https://github.com/VQ-Vinh/VHF/releases),
đối chiếu file SHA-256 đi kèm, sau đó quét QR trong ứng dụng. Người sử dụng APK
không cần Flutter, Android SDK hoặc Emulator.

`enable_station_api.bat` mặc định kết nối Laptop Station với Cloud API. Người
vận hành chỉ cần Internet, không cần Google Cloud CLI, ADC hoặc dùng chung Wi-Fi
với điện thoại.

Chỉ lập trình viên cần chạy backend local mới sử dụng ADC:

```bat
gcloud auth application-default login
enable_station_api.bat -LocalApi
```

Khi phát triển Android và muốn mở thêm Emulator + Flutter:

```bat
enable_station_api.bat -WithMobile
```

## Raspberry Pi/Linux

```bash
./scripts/setup/setup.sh
./apps/linux/run.sh
```

## Phát triển Android

Tạo file cấu hình từ `apps/android/config/staging.example.json`, sau đó:

```bat
run_android_emulator.bat
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
build_android_apk.bat
```

APK được cấu hình cho điện thoại thật và tự chọn IP LAN của laptop. Trên
Raspberry Pi:

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

APK/AAB và bộ cài là artifact phát hành, không được commit vào repository.
Người phát hành tải APK đã ký và file checksum `.sha256` lên GitHub Releases.

## Cấu hình và bảo mật

Config client nằm tại:

- `apps/windows/config/default.toml`
- `apps/linux/config/default.toml`
- `apps/android/config/*.example.json`

Không commit service-account JSON, private key, token, signing key hoặc credential.
Firebase Web API key và OAuth client ID trong client chỉ là định danh public; mọi
quyền nghiệp vụ vẫn được kiểm tra tại API.

Các thư mục `.venv/`, `.secrets/`, `VHF_Storage/`, `stations/`, Terraform state
và cấu hình Android thật đều được Git bỏ qua.

Hướng dẫn staging đầy đủ: [docs/staging-e2e-test-guide.md](docs/staging-e2e-test-guide.md).
