# Cài đặt và phát triển PRANA ELEX

Tài liệu này dành cho người triển khai Station và developer cần chạy, kiểm thử
hoặc build PRANA ELEX. Hướng dẫn thao tác trên App nằm trong
[Hướng dẫn sử dụng](user-guide.md); lỗi thiết bị và runtime nằm trong
[Troubleshooting](troubleshooting.md).

## Yêu cầu

### Người sử dụng

- Điện thoại Android và APK PRANA ELEX.
- Laptop Windows 10/11 hoặc Raspberry Pi 4B làm Station.
- USB SoundCard có audio input cho RX và audio output cho TX.
- Kết nối Internet cho App và Station.
- Tài khoản PRANA ELEX đã xác minh email và còn hiệu lực.

### Developer Windows

- Git, PowerShell và Windows 10/11 x64.
- Python 3.11 trở lên.
- Flutter stable 3.44.8 trở lên, Android SDK và JDK 17 nếu phát triển Android.
- Google Cloud CLI chỉ khi chạy backend local. Station dùng Cloud không cần
  `gcloud`, ADC hoặc service-account JSON.

### Raspberry Pi

- Raspberry Pi 4B, Raspberry Pi OS Bookworm ARM64.
- `alsa-utils` để sử dụng `arecord` và `amixer`.
- Python 3.11 trở lên cùng các gói build audio nếu chạy từ source.

## Setup developer trên Windows

Mở PowerShell tại thư mục muốn chứa source:

```powershell
git clone https://github.com/VQ-Vinh/VHF.git
cd VHF
.\scripts\setup\setup.bat
```

Setup tạo `.venv\dev` cho core/Station, `.venv\backend` cho API/Admin và cài
dependency theo đúng package boundary. Nếu setup lỗi, sửa dependency rồi chạy
lại script; không thay bằng system Python.

## Laptop Station

### Provision và tạo QR

```powershell
.\apps\windows\scripts\generate-station-qr.bat
```

QR PNG/SVG được tạo trong `stations/`. QR chứa thông tin kích hoạt Station;
không commit hoặc chia sẻ công khai ảnh này.

### Chạy với Cloud API

```powershell
.\enable_station_api.bat
```

Script kiểm tra Cloud API rồi chạy Laptop Station ẩn nền. Log và PID nằm trong
`.prana/logs/dev/` và `.prana/runtime/`. Chạy lại cùng lệnh sẽ restart tiến
trình do script quản lý và nhận source/config mới nhất.

Chạy Station cùng Android Emulator:

```powershell
.\enable_station_api.bat -WithMobile
```

Kết nối USB SoundCard, sau đó mở **Cài đặt Station** trên App, quét lại thiết bị
và chọn đúng `RX INPUT` cùng `TX OUTPUT`. START chỉ thành công khi input đã chọn
tồn tại.

## Raspberry Pi Station

### Cài đặt bằng release

Trên Raspberry Pi OS Bookworm ARM64 mới flash, cắm mạng và USB SoundCard rồi
chạy:

```bash
curl -fsSL https://raw.githubusercontent.com/VQ-Vinh/VHF/main/install.sh | sudo bash
```

Installer tải `.deb` mới nhất, kiểm tra SHA-256, cài bằng `apt`, đặt gain micro,
provision thiết bị và in QR trên terminal. Quét QR đó bằng PRANA ELEX Android.

Nếu chưa publish release, cài từ file build tay:

```bash
sudo ./install.sh --deb prana-elex_1.1.0_arm64.deb
```

Các tùy chọn:

- `--version <tag>`: ghim phiên bản;
- `--skip-provision`: chỉ cài package;
- `--skip-audio-gain`: không thay đổi gain ALSA.

Chạy lại installer để nâng cấp; Setup ID cũ được giữ nguyên và danh tính mới
không được tạo.

> [!CAUTION]
> Không nhân bản thẻ nhớ đã provision. `station_id`, private key Ed25519 và mã
> kích hoạt gắn với từng máy. Mỗi Pi phải tự chạy `install.sh`.

Kiểm tra service:

```bash
systemctl status prana-station
journalctl -u prana-station -f
```

### Phát triển từ source

Người dựng thiết bị nên dùng package release. Các bước sau chỉ dành cho người
sửa code:

```bash
git clone https://github.com/VQ-Vinh/VHF.git
cd VHF

sudo apt update
sudo apt install -y \
  python3-venv python3-dev build-essential \
  alsa-utils portaudio19-dev libsndfile1-dev libasound2-dev

./scripts/setup/setup.sh
```

Provision và tạo QR:

```bash
.venv/dev/bin/prana-station-provision \
  --config apps/linux/config/default.toml \
  --output ~/prana-station-label
```

Không chia sẻ private identity trong `~/.config/prana-elex/`. Chạy Station:

```bash
./apps/linux/run.sh
```

### Chạy bằng systemd

Package `.deb` tự cài unit. Quản lý service bằng:

```bash
sudo systemctl enable --now prana-station
sudo systemctl status prana-station --no-pager
sudo journalctl -u prana-station -f
```

Sau khi cập nhật source/config của bản development:

```bash
sudo systemctl restart prana-station
```

## Android App

### Cài APK trên điện thoại thật

1. Tải APK và checksum từ [GitHub Releases](https://github.com/VQ-Vinh/VHF/releases).
2. Đối chiếu SHA-256:

   ```powershell
   Get-FileHash .\PRANA_ELEX.apk -Algorithm SHA256
   ```

3. Cho phép cài ứng dụng từ nguồn đã tải APK nếu Android yêu cầu.
4. Cài APK; chỉ cấp camera/microphone khi dùng chức năng tương ứng.

Người dùng APK không cần Flutter, Android Studio hoặc Google Cloud CLI.

### Phát triển Android

Sao chép cấu hình mẫu:

```text
apps/android/config/staging.example.json
→ apps/android/config/staging.json
```

Điền Firebase public client config của staging rồi chạy từ repository root:

```powershell
.\run_android_emulator.bat
```

Tùy chọn thường dùng:

```powershell
.\run_android_emulator.bat -EmulatorResolution 1080x1920
.\run_android_emulator.bat -Flavor production
```

Chạy Flutter thủ công:

```powershell
cd apps\android
flutter pub get
flutter run --flavor staging --dart-define-from-file=config/staging.json
```

Trong terminal Flutter, nhấn `r` để Hot Reload, `R` để Hot Restart và `q` để
dừng App. Kiểm tra điện thoại thật kết nối ADB:

```powershell
& "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" devices -l
```

## iOS

Ứng dụng Flutter có thư mục nền tảng `apps/android/ios/`, nhưng phạm vi iOS hiện
tại **chỉ tới Simulator**, và chỉ chạy trên CI.

### Vì sao không build được tại chỗ

Apple yêu cầu macOS và Xcode để compile iOS, chạy Simulator và ký gói. Máy phát
triển của dự án chạy Windows, nên không có cách nào build iOS tại chỗ — đây là
giới hạn của Apple chứ không phải của dự án.

Thay vào đó, job `iOS simulator build` trong `.github/workflows/ci.yml` chạy trên
`macos-latest`. Nó kích hoạt khi PR đụng `apps/android/` (trừ riêng thư mục
`android/`), build cho Simulator, khởi động Simulator, mở app và chụp màn hình.

### Xem kết quả

Mở lần chạy CI của PR, tải artifact `ios-simulator`:

- `Runner-simulator.app.zip` — kéo thả vào Simulator trên một máy Mac là chạy
  được. **Không cài được lên iPhone thật.**
- `launch-at-*s.png` — ảnh chụp ở ba mốc trong quá trình khởi động.
- `Podfile.lock` — sinh trên runner; commit vào repo để ghim phiên bản pod.

### Những gì iOS chưa có

- **Không có file cài lên máy thật.** `.ipa`, TestFlight và ad-hoc đều bắt buộc
  Apple Developer Program ($99/năm), hiện dự án không có.
- **Không có flavor.** Flavor trên iOS cần Xcode scheme; bản build dùng
  `--dart-define-from-file` để nạp cấu hình.
- **Không kiểm được trên Simulator:** camera (Simulator không có camera nên quét
  QR không chạy), micro (runner không có input audio nên TX không kiểm được),
  Google Sign-In (chưa cấu hình iOS OAuth client).
- **Icon vẫn là icon mặc định của Flutter**, chưa có bộ icon PRANA như Android.

Ảnh chụp Simulator dùng để xác nhận app **compile và khởi động được** trên iOS.
Việc kiểm tra bố cục giao diện vẫn dựa vào widget test, vốn phủ rộng hơn nhiều —
xem `apps/android/test/responsive_screens_test.dart`.

## Backend local

Backend local chỉ dành cho developer. Đăng nhập ADC:

```powershell
gcloud auth application-default login
```

Chạy API local cùng Laptop Station:

```powershell
.\enable_station_api.bat -LocalApi
```

API chạy ở port `8080`; log nằm trong `.prana/logs/dev/`. Không thêm
service-account JSON vào repository.

Chạy API trực tiếp khi cần debug:

```powershell
.\.venv\backend\Scripts\python.exe -m uvicorn services.prana_api.main:app --reload --port 8080
```

Web Admin là service riêng được bảo vệ bằng Google IAP; quyền Admin không được
suy ra từ quyền đăng nhập App.

## Kiểm thử

Không chạy bare `python -m pytest`: không environment nào chứa mọi dependency.
Từ repository root:

```powershell
# Core, Linux Station, packaging và repo rules
.\.venv\dev\Scripts\python.exe -m pytest tests/core tests/linux tests/packaging tests/conventions

# Windows Station
.\.venv\dev\Scripts\python.exe -m pytest tests/windows

# API và Admin
.\.venv\backend\Scripts\python.exe -m pytest tests/api tests/admin
```

Android:

```powershell
cd apps\android
flutter analyze
flutter test
```

Pull Request phải vượt qua required check `CI / gate`.

## Build và phát hành

### Android APK

```powershell
.\build_android_apk.bat
```

Các lựa chọn chi tiết:

```powershell
.\apps\android\build.bat -Flavor staging -BuildMode release -PhysicalDevice
.\apps\android\build.bat -Flavor production -PhysicalDevice
.\apps\android\build.bat -PhysicalDevice -Clean
```

Production release yêu cầu keystore hợp lệ. Không commit keystore hoặc signing
password. Không tự động build APK sau thay đổi UI thông thường.

### Linux ARM64

Build trực tiếp trên Raspberry Pi 4B Bookworm ARM64:

```bash
./buildlinux
```

Để build và publish `.deb` từ Pi bằng GitHub CLI:

```bash
curl -fsSL https://raw.githubusercontent.com/VQ-Vinh/VHF/main/release-pi.sh | bash
```

Lệnh này clone/cập nhật source tại `~/prana-elex-src`, chạy `./buildlinux` và
upload package cùng checksum. Cần chạy `gh auth login` trước. Lần đầu có thể mất
15–30 phút do biên dịch dependency native; các lần sau tái sử dụng checkout và
venv.

Artifact local nằm trong:

```text
installers/android/
installers/linux/
installers/windows/
```

Không commit artifact release hoặc thư mục build.

## Lưu trữ và log

Station lưu dữ liệu theo cấu trúc:

```text
VHF_Storage/
├── RX/
│   ├── audio/YYYY/MM/DD/
│   └── results/YYYY/MM/DD/
└── TX/
    ├── source/YYYY/MM/DD/
    ├── output/YYYY/MM/DD/
    └── results/YYYY/MM/DD/
```

RX/TX dùng tên `YYYYMMDD_HHMMSS_####`. Dữ liệu legacy trong
`VHF_Storage/audio` và `VHF_Storage/results` vẫn được đọc, không bắt buộc
migration.

Log development Windows:

```text
.prana/logs/dev/api.stdout.log
.prana/logs/dev/api.stderr.log
.prana/logs/dev/station.stdout.log
.prana/logs/dev/station.stderr.log
```

Log Raspberry Pi:

```bash
sudo journalctl -u prana-station -f
```
