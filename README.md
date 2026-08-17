# PRANA ELEX

PRANA ELEX là hệ thống hỗ trợ nhận dạng, dịch và truyền thông tin thoại VHF gần
thời gian thực. Hệ thống gồm Android App, Station chạy trên Windows hoặc
Raspberry Pi, PRANA API và các dịch vụ Cloud.

Luồng RX:

```text
VHF → USB SoundCard → Station → Cloud AI → Android App
```

Luồng TX hiện tại:

```text
Android Hold-to-talk → Cloud AI/TTS → Station → GPIO17 PTT + audio output → VHF
```

Station thực thi interlock half-duplex bằng phần mềm: tạm dừng capture RX, kích
PTT, phát TX và chỉ tiếp tục RX nếu Station vẫn được START. Raspberry Pi có thể
điều khiển PTT active-high bằng GPIO17; Laptop Station dùng PTT thủ công. Hệ
thống chưa sensing channel busy và phần RF vẫn phải được kiểm thử theo cấu hình
VHF/mạch cách ly thực tế.

## Mục lục

- [Thành phần hệ thống](#thành-phần-hệ-thống)
- [Yêu cầu](#yêu-cầu)
- [Clone và setup trên Windows](#clone-và-setup-trên-windows)
- [Chạy Laptop Station](#chạy-laptop-station)
- [Setup Raspberry Pi Station](#setup-raspberry-pi-station)
- [Cài và chạy Android App](#cài-và-chạy-android-app)
- [Hướng dẫn sử dụng App](#hướng-dẫn-sử-dụng-app)
- [Chạy backend local](#chạy-backend-local)
- [Kiểm thử](#kiểm-thử)
- [Build artifact](#build-artifact)
- [Lưu trữ và log](#lưu-trữ-và-log)
- [Xử lý lỗi thường gặp](#xử-lý-lỗi-thường-gặp)
- [Bảo mật và đóng góp](#bảo-mật-và-đóng-góp)

## Thành phần hệ thống

```text
apps/windows/          Laptop Station, WASAPI và bộ cài Windows
apps/linux/            Raspberry Pi/Linux Station, ALSA và arecord
apps/android/          Flutter Android App
packages/prana_core/   Pipeline, VAD, storage và Station protocol dùng chung
services/prana_api/    Public FastAPI service
services/prana_admin/  Web Admin được bảo vệ bằng Google IAP
infra/                 Terraform và Firebase rules
tests/                 Test theo từng subsystem
docs/                  Kiến trúc, CI/CD và kịch bản kiểm thử
```

Android và Station chỉ cần kết nối Internet; hai thiết bị không cần cùng mạng
LAN và không cần mở inbound port. Credential Cloud, AI prompt và quyền truy cập
dữ liệu chỉ nằm ở backend.

Tài liệu kỹ thuật chi tiết:

- [Kiến trúc tổng quát](docs/architecture.md)
- [Kiến trúc Android và Station](docs/android-station-architecture.md)
- [Sơ đồ tổng quan](docs/architecture-overview.md)
- [CI/CD](docs/cicd.md)
- [Kịch bản kiểm thử Android và Web Admin](docs/android-web-admin-test-scenarios.md)

## Yêu cầu

### Người sử dụng

- Điện thoại Android và APK PRANA ELEX.
- Laptop Windows 10/11 hoặc Raspberry Pi 4B làm Station.
- USB SoundCard có audio input cho RX và audio output cho TX.
- Kết nối Internet cho App và Station.
- Tài khoản PRANA ELEX đã xác minh email và còn hiệu lực.

### Lập trình viên Windows

- Git.
- Python 3.11 trở lên.
- PowerShell và Windows 10/11 x64.
- Flutter stable 3.44.8 trở lên, Android SDK và JDK 17 nếu phát triển Android.
- Google Cloud CLI chỉ khi chạy backend local. Chạy Station với Cloud không cần
  `gcloud`, ADC hoặc service-account JSON.

### Raspberry Pi

- Raspberry Pi 4B, Raspberry Pi OS Bookworm ARM64.
- Python 3.11 trở lên.
- `alsa-utils` để sử dụng `arecord`/`amixer`.
- Các gói build audio khi chạy từ source:

  ```bash
  sudo apt update
  sudo apt install -y \
    python3-venv python3-dev build-essential \
    alsa-utils portaudio19-dev libsndfile1-dev libasound2-dev
  ```

## Clone và setup trên Windows

Mở PowerShell hoặc Command Prompt:

```powershell
git clone https://github.com/VQ-Vinh/VHF.git
cd VHF
```

Chạy setup từ thư mục gốc:

```powershell
.\scripts\setup\setup.bat
```

Script sẽ:

1. kiểm tra Python;
2. tạo `.venv\dev` cho core và Station;
3. tạo `.venv\backend` cho API/Admin;
4. cài dependency theo đúng package boundary;
5. tạo các thư mục lưu trữ cục bộ cần thiết.

Nếu setup thất bại, không chạy bằng system Python. Sửa dependency rồi chạy lại
script; môi trường đã tạo sẽ được tái sử dụng.

## Chạy Laptop Station

### 1. Tạo QR ghép Station

Sau khi setup:

```powershell
.\generate_station_qr.bat
```

QR PNG/SVG được tạo trong thư mục `stations/`. QR chứa thông tin kích hoạt
Station; không commit hoặc chia sẻ công khai ảnh này.

### 2. Kết nối Cloud API và chạy Station

```powershell
.\enable_station_api.bat
```

Script kiểm tra Cloud API rồi chạy Laptop Station ẩn nền. Log và PID nằm trong:

```text
.prana/logs/dev/
.prana/runtime/
```

Chạy lại cùng lệnh sẽ restart tiến trình do script quản lý và nhận source/config
mới nhất.

Muốn chạy đồng thời Station và Android Emulator:

```powershell
.\enable_station_api.bat -WithMobile
```

### 3. Kết nối USB SoundCard

- Cổng input nhận audio từ VHF RX.
- Cổng output đưa audio TX tới loa, bộ test hoặc VHF TX.
- Vào **Cài đặt Station** trên App, quét lại thiết bị và chọn đúng `RX INPUT`
  cùng `TX OUTPUT`.
- START Station chỉ thành công khi thiết bị RX input tồn tại.

## Setup Raspberry Pi Station

### 1. Clone và cài dependency

Trên Raspberry Pi:

```bash
git clone https://github.com/VQ-Vinh/VHF.git
cd VHF

sudo apt update
sudo apt install -y \
  python3-venv python3-dev build-essential \
  alsa-utils portaudio19-dev libsndfile1-dev libasound2-dev

./scripts/setup/setup.sh
```

### 2. Kiểm tra USB SoundCard

```bash
arecord -l
aplay -l
```

Thu WAV raw để kiểm tra phần cứng trước khi chạy pipeline:

```bash
arecord -D hw:CARD=Device,DEV=0 \
  -t wav -f S16_LE -c 1 -r 44100 -d 10 rx-test.wav
```

Nếu `CARD=Device` không tồn tại, dùng card/device được `arecord -l` trả về.

Raspberry Pi Station phải capture RX trực tiếp qua ALSA/`arecord`; không đổi
lại sang PyAudio callback. Cấu hình đã kiểm chứng với USB SoundCard hiện tại:

```text
Mic Capture: +15 dB (18/28)
min_silence_duration_ms: 1500
max_segment_duration_ms: 15000
```

Đặt và lưu gain:

```bash
amixer -c 3 cset name='Mic Capture Volume' 18
sudo alsactl store 3
```

Card index có thể thay đổi giữa các thiết bị; kiểm tra lại bằng `arecord -l` và
`amixer -c <card>`.

### 3. Provision và tạo QR

```bash
.venv/dev/bin/prana-station-provision \
  --config apps/linux/config/default.toml \
  --output ~/prana-station-label
```

In hoặc chuyển QR label cho người sở hữu Station. Không chia sẻ private identity
trong `~/.config/prana-elex/`.

### 4. Chạy từ source

```bash
./apps/linux/run.sh
```

### 5. Chạy bằng systemd

Nếu đã cài gói `.deb`:

```bash
sudo systemctl enable --now prana-station
sudo systemctl status prana-station --no-pager
sudo journalctl -u prana-station -f
```

Sau khi cập nhật source hoặc config của bản development:

```bash
sudo systemctl restart prana-station
```

## Cài và chạy Android App

### Người sử dụng điện thoại thật

1. Tải APK và file checksum từ
   [GitHub Releases](https://github.com/VQ-Vinh/VHF/releases).
2. Đối chiếu SHA-256 trước khi cài:

   ```powershell
   Get-FileHash .\PRANA_ELEX.apk -Algorithm SHA256
   ```

3. Cho phép cài ứng dụng từ nguồn đã tải APK nếu Android yêu cầu.
4. Cài APK, mở App và cấp quyền camera/microphone khi sử dụng chức năng tương
   ứng.

Người dùng APK không cần Flutter, Android Studio hoặc Google Cloud CLI.

### Lập trình viên Android

Sao chép file cấu hình mẫu:

```text
apps/android/config/staging.example.json
→ apps/android/config/staging.json
```

Điền cấu hình Firebase client public của staging, sau đó từ thư mục gốc chạy:

```powershell
.\run_android_emulator.bat
```

Tùy chọn thường dùng:

```powershell
.\run_android_emulator.bat -EmulatorResolution 1080x1920
.\run_android_emulator.bat -Flavor production
```

Trong terminal Flutter:

- `r`: Hot Reload.
- `R`: Hot Restart.
- `q`: dừng App.

Chạy thủ công:

```powershell
cd apps\android
flutter pub get
flutter run --flavor staging --dart-define-from-file=config/staging.json
```

Điện thoại thật kết nối ADB có thể được kiểm tra bằng:

```powershell
& "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" devices -l
```

## Hướng dẫn sử dụng App

### 1. Đăng ký và đăng nhập

1. Mở App và chọn **Tạo tài khoản** hoặc đăng nhập bằng Google.
2. Với Email/Password, mở email xác minh rồi quay lại App và nhấn làm mới.
3. Mở **Tài khoản** để xem gói, quota, thiết bị và Station đang sở hữu.

Không chia sẻ mật khẩu, token hoặc QR Station trong ảnh chụp báo lỗi.

### 2. Ghép Station

1. Bảo đảm Station service đang online và có Internet.
2. Trong danh sách Station, chọn **Ghép trạm**.
3. Quét QR cố định trên Laptop/Raspberry Pi hoặc nhập Setup ID và Activation
   Code.
4. Pairing code tạm thời 8 ký tự chỉ dùng cho Station/luồng cũ còn tương thích.
5. Sau khi ghép thành công, Station xuất hiện trong danh sách của tài khoản.

Một Station chỉ thuộc một owner tại một thời điểm. Muốn chuyển owner, phải gỡ
Station hoặc thực hiện transfer theo quy trình Admin.

### 3. Cấu hình Station

Mở Station rồi nhấn biểu tượng bánh răng:

1. Nhấn **Quét lại thiết bị** nếu vừa cắm USB SoundCard.
2. Chọn đúng `RX INPUT` có input channel.
3. Chọn đúng `TX OUTPUT` có output channel.
4. Quay lại màn vận hành và chờ Station đồng bộ desired state.

Nếu App báo không tìm thấy USB SoundCard, kết nối lại thiết bị rồi nhấn
**Thử lại**. Không để START mắc ở trạng thái chờ vô hạn.

### 4. Sử dụng RX

1. Chọn ngôn ngữ đầu vào hoặc để chế độ nhận diện phù hợp với cấu hình App.
2. Chọn ngôn ngữ đầu ra.
3. Nhấn **START** và chờ badge chuyển sang `RX LISTENING`.
4. Phát audio VHF vào USB SoundCard.
5. Kết quả xuất hiện trong **Bản dịch trực tiếp** với thời gian, ngôn ngữ và độ
   tin cậy.
6. Nhấn biểu tượng loa để nghe lại:
   - source khác target: App đọc bản dịch bằng TTS;
   - source trùng target: App phát WAV nguồn;
   - không tải được WAV nguồn: App fallback sang TTS transcript.
7. Bật/tắt auto-play bằng nút audio trên phần Live Translations.

RX tạo segment khi gặp khoảng nghỉ đã cấu hình hoặc đạt giới hạn 15 giây. Một
lượt nói dài có thể xuất hiện thành nhiều card liên tiếp; đây là hành vi bình
thường để giới hạn latency và kích thước request.

### 5. Sử dụng TX Hold-to-talk

TX chỉ hoạt động khi Station online, đã START và không có command đang chờ.

1. Chọn **Ngôn ngữ TX** ở bên phải bottom dock.
2. Nhấn giữ **GIỮ ĐỂ NÓI** trong suốt lúc nói.
3. Khi dock chuyển đỏ và timer chạy, App đang thu microphone điện thoại.
4. Thả nút để kết thúc. App upload WAV và xử lý nhận dạng/dịch.
5. Tại màn review:
   - transcript gốc chỉ đọc;
   - bản dịch/nội dung phát có thể chỉnh sửa;
   - nội dung không được rỗng và tối đa 2.000 ký tự.
6. Chọn **Phát** để Cloud tạo audio, nối khoảng lặng và từ “Over”; chọn **Hủy**
   để bỏ draft.
7. Theo dõi trạng thái:

   ```text
   Đang tổng hợp → Đang chờ Station → Station đang phát → Hoàn tất
   ```

Station dừng RX trước khi playback và chỉ resume RX nếu desired state vẫn là
START. Job lỗi không tự phát lại để tránh truyền trùng; chỉ nhấn **Thử lại** khi
Station đã online và START trở lại.

Trên Raspberry Pi đã bật cấu hình PTT, Station tạm dừng capture RX, đưa GPIO17
lên HIGH, chờ key-up 400 ms, phát audio, giữ tail 300 ms rồi hạ GPIO. Watchdog
122 giây luôn nhả PTT nếu audio driver bị treo. Nếu GPIO không khởi tạo được,
RX và heartbeat vẫn chạy nhưng App khóa TX và báo `PTT_UNAVAILABLE`. Laptop
Station tiếp tục dùng PTT thủ công; hệ thống chưa có channel-busy sensing.

### 6. Xem lịch sử

1. Nhấn biểu tượng **Lịch sử** trong phần Live Translations.
2. Chọn tab `RX` hoặc `TX`; tab mặc định là RX.
3. Chọn ngày để xem log chi tiết.
4. Tab RX hỗ trợ xem transcript/bản dịch và playback theo entitlement.
5. Tab TX hiển thị transcript, nội dung đã phát, trạng thái, attempt và dấu hiệu
   nội dung đã chỉnh sửa; nút loa phát output WAV nếu job đã tạo audio.

Quyền xem lịch sử và độ trễ mở khóa phụ thuộc gói hiện tại.

### 7. STOP, offline và đăng xuất

- Nhấn **Dừng** để đặt desired state `running=false`.
- Nếu Station đang offline, STOP vẫn được lưu để Station không tự chạy RX khi
  kết nối lại.
- Nếu mất mạng giữa TX, App hiển thị kết quả chưa xác nhận; chờ backend giải
  phóng job rồi mới retry thủ công.
- Đăng xuất, đổi Station hoặc đưa App xuống background sẽ dừng playback đang
  chạy trên điện thoại.

## Chạy backend local

Backend local chỉ dành cho lập trình viên. Đăng nhập ADC:

```powershell
gcloud auth application-default login
```

Sau đó chạy API local và Laptop Station:

```powershell
.\enable_station_api.bat -LocalApi
```

Script chạy API ở port `8080`, kiểm tra health và lưu log trong
`.prana/logs/dev/`. Không thêm service-account JSON vào repository.

Chạy API trực tiếp khi cần debug:

```powershell
.\.venv\backend\Scripts\python.exe -m uvicorn services.prana_api.main:app --reload --port 8080
```

Web Admin là service riêng và được bảo vệ bằng Google IAP; quyền truy cập Admin
không được suy ra từ quyền đăng nhập App.

## Kiểm thử

### Python

Từ thư mục gốc trên Windows PowerShell:

```powershell
$env:PYTHONPATH="packages/prana_core/src;apps/windows/src;apps/linux/src;."

.\.venv\dev\Scripts\python.exe -m pytest tests/core tests/windows tests/linux tests/packaging

.\.venv\backend\Scripts\python.exe -m pytest tests/api tests/admin
```

### Flutter

```powershell
cd apps\android
flutter analyze
flutter test
```

Pull Request phải vượt qua required check `CI / gate`. Không bypass gate hoặc
deploy image thủ công đè lên staging revision do CI quản lý.

## Build artifact

### Android APK

Từ thư mục gốc:

```powershell
.\build_android_apk.bat
```

Các lựa chọn khác:

```powershell
.\apps\android\build.bat -Flavor staging -BuildMode release -PhysicalDevice
.\apps\android\build.bat -Flavor production -PhysicalDevice
.\apps\android\build.bat -PhysicalDevice -Clean
```

Production release yêu cầu keystore hợp lệ. Không commit keystore hoặc signing
password.

### Linux ARM64

Build trực tiếp trên Raspberry Pi 4B Bookworm ARM64:

```bash
./buildlinux
```

Script kiểm tra kiến trúc, hệ điều hành, dung lượng và dependency trước khi tạo
bundle cùng gói `.deb`.

Artifact được đặt trong:

```text
installers/android/
installers/linux/
installers/windows/
```

Artifact release và thư mục build không được commit vào Git.

## Lưu trữ và log

Station lưu dữ liệu mới theo cấu trúc:

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

Log Raspberry Pi systemd:

```bash
sudo journalctl -u prana-station -f
```

## Xử lý lỗi thường gặp

### App không thấy Station online

- Kiểm tra Internet trên App và Station.
- Kiểm tra service/process Station.
- Xem heartbeat và log thay vì chỉ restart App.
- Android và Station không cần cùng Wi-Fi.

### START mắc ở “Đang bật”

- Kiểm tra USB SoundCard bằng `arecord -l` hoặc thiết bị Windows.
- Mở Cài đặt Station và quét lại device.
- Nếu Station báo `AUDIO_INPUT_DEVICE_NOT_FOUND`, kết nối input rồi nhấn
  **Thử lại** hoặc **Dừng**.

### Raspberry Pi RX đứt đoạn/nghẹt

- Xác nhận process capture là `arecord`, không phải PyAudio callback:

  ```bash
  ps -ef | grep arecord
  ```

- Thu raw WAV và nghe trước khi chỉnh VAD.
- So sánh WAV raw với WAV trong `VHF_Storage/RX/audio`.
- Kiểm tra Mic Capture gain; gain quá cao gây clipping và âm chói.

### TX dịch được nhưng không phát

- Station phải online và đã START.
- Kiểm tra `TX OUTPUT` có output channel.
- Kiểm tra job ở `synthesizing`, `queued`, `transmitting` hay `failed`.
- Job lỗi không tự replay; retry thủ công sau khi sửa Station/output.

### Android không nhận Hot Reload

Không cần chạy lại toàn bộ emulator. Trong terminal `flutter run`, nhấn `r`. Nếu
thay native manifest, Gradle, permission hoặc plugin thì cần Hot Restart hoặc
chạy lại App.

## Bảo mật và đóng góp

- Không commit service-account JSON, private key, token, signing key, Terraform
  state hoặc config Android thật.
- Firebase Web API key/OAuth client ID trong client là định danh public; quyền
  nghiệp vụ vẫn được kiểm tra tại API.
- Các thư mục `.venv/`, `.secrets/`, `.prana/`, `VHF_Storage/`, `stations/` và
  artifact build phải được Git bỏ qua.
- Dùng Conventional Commits, ví dụ `fix(linux): ...`, `feat(tx): ...`,
  `docs: ...`.
- Tách thay đổi thành commit logic, chạy test phù hợp và mở Pull Request; `main`
  được bảo vệ bởi CI gate.

Xem thêm quy tắc dành cho coding agent và contributor tại [AGENTS.md](AGENTS.md).
