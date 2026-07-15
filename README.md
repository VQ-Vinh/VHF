# PRANA ELEX

**Nghe và dịch liên lạc VHF hàng hải** — bắt âm thanh từ thiết bị thu, tự động nhận diện giọng nói, phiên dịch và hiển thị kết quả real-time.

---

## Dành cho người mới bắt đầu

### Bước 1: Cài đặt (làm một lần)

**Windows:**
```cmd
scripts\setup\setup.bat
```

**Linux / Raspberry Pi:**
```bash
./scripts/setup/setup.sh
```

Script sẽ tự tạo môi trường ảo, cài đặt thư viện, tạo thư mục lưu dữ liệu.

### Bước 2: Đặt Google Cloud JSON key

Gemini Vertex AI và Google Cloud Storage dùng chung một service-account JSON key; ứng dụng không dùng API key hoặc ADC. Khi chạy từ source, đặt key tại:

```text
.secrets/gcs-service-account.json
```

Thư mục `.secrets/` đã được Git bỏ qua. Không commit JSON key vào repository.

Khi cài bằng `release/windows/PRANA_ELEX_Setup_1.0.0_x64.exe`, installer sẽ yêu cầu chọn
service-account JSON ở bước **Google Cloud Credentials**. Key được sao chép trong
lúc cài đặt và đường dẫn được ghi vào `settings.json`; key không được nhúng sẵn
trong file Setup.

Khi dùng bản portable trong `dist/windows/PRANA_ELEX/`, tạo cùng cấu trúc bên cạnh file
thực thi:

```text
PRANA_ELEX.exe
.secrets/
└── gcs-service-account.json
```

Có thể dùng một vị trí khác bằng biến môi trường cố định:

```cmd
setx PRANA_ELEX_GOOGLE_CREDENTIALS "D:\secure\gcs-service-account.json"
```

Sau khi dùng `setx`, đóng và mở lại ứng dụng để nhận biến môi trường mới.

### Bước 3: Chạy thôi

**Có giao diện đồ hoạ (GUI):**
```cmd
run_dev.bat
```

**Chạy trên console (không cần màn hình):**
```cmd
scripts\dev\run-cli.bat
```

**Nếu có file WAV muốn xử lý sẵn:**
```cmd
scripts\dev\run-cli.bat batch file1.wav file2.wav
```

### Đóng gói Windows x64

Build sạch toàn bộ ứng dụng bằng một lệnh tại thư mục gốc dự án:

```cmd
buildwin.bat
```

Nếu đã cài Inno Setup 6, lệnh trên đồng thời tạo bộ cài dành cho người dùng:

```text
release/windows/PRANA_ELEX_Setup_1.0.0_x64.exe
```

File `dist\windows\PRANA_ELEX\PRANA_ELEX.exe` là bản đóng gói portable:

```cmd
dist\windows\PRANA_ELEX\PRANA_ELEX.exe
```

`build.bat` hiện chỉ là alias tạm thời cho `buildwin.bat` và sẽ bị loại bỏ ở
major release sau.

### Đóng gói Raspberry Pi 4B ARM64

Chạy trực tiếp trên Raspberry Pi 4B dùng Raspberry Pi OS Desktop Bookworm 64-bit:

```bash
./buildlinux
```

Lệnh này chỉ tạo artifact Linux ARM64; nó không đụng vào output Windows:

```text
dist/linux-arm64/PRANA_ELEX/
release/linux-arm64/prana-elex_1.0.0_arm64.deb
```

Cài và chạy gói trên Pi:

```bash
sudo apt install ./release/linux-arm64/prana-elex_1.0.0_arm64.deb
prana-elex
```

Lần chạy đầu sẽ yêu cầu chọn thư mục dữ liệu và service-account JSON. Cấu hình
được lưu tại `~/.config/prana-elex/settings.json`, credentials được sao chép tới
`~/.config/prana-elex/gcs-service-account.json` với mode `0600`, và dữ liệu mặc
định nằm ở `~/PRANA_ELEX_Data`. Gỡ gói bằng `apt remove prana-elex` không xóa các
tệp người dùng này. Autostart mặc định tắt và có thể bật trong Settings.

---

## Có gì bên trong?

App có 2 chế độ:

### Màn hình desktop (GUI)

Giao diện đồ hoạ cho Windows — bạn sẽ thấy:

- **Luồng dịch real-time** — từng câu nói được hiển thị dưới dạng bubble, kèm transcript gốc + bản dịch
- **Chọn ngôn ngữ đầu ra** — muốn dịch ra tiếng Việt, Anh, Trung, Nhật, Hàn? Bấm một cái là xong
- **Cài đặt thiết bị thu** — chọn đầu vào là USB SoundCard hay loopback (bắt âm thanh từ loa máy tính)
- **Lịch sử** — coi lại các phiên trước, tìm kiếm nội dung
- **Thu nhỏ xuống khay hệ thống** — để đó chạy ngầm

### Console (CLI)

Dành cho ai thích gõ lệnh hoặc chạy trên máy không màn hình (Raspberry Pi chẳng hạn):

- Lần đầu chạy sẽ hỏi bạn muốn dùng thiết bị nào, ngôn ngữ nào
- Hiển thị real-time trên terminal với thông tin chi tiết (confidence, latency,...)
- Hỗ trợ xử lý batch từ file WAV có sẵn

---

## Thiết bị âm thanh

App bắt âm thanh từ **USB SoundCard** hoặc **loopback** (âm thanh từ loa máy tính).

Mặc định dùng device index 17 trong file config. Nếu cần đổi:

```toml
# config/default.toml
[audio]
capture_mode = "device"       # "device" hoặc "loopback"
device_index = 17              # số thiết bị của bạn
```

Để xem danh sách thiết bị, dùng lệnh sau trong Python:

```python
import pyaudiowpatch as pyaudio
pa = pyaudio.PyAudio()
for i in range(pa.get_device_count()):
    info = pa.get_device_info_by_index(i)
    print(f'[{i}] {info["name"]} | inputs={info["maxInputChannels"]} | sr={info["defaultSampleRate"]}')
pa.terminate()
```

---

## Dữ liệu lưu ở đâu?

Khi chạy từ source, mọi dữ liệu được lưu trong thư mục `VHF_Storage/` ở gốc dự án:

```
VHF_Storage/
├── audio/        ← file WAV từng đoạn hội thoại
└── results/      ← file JSON kết quả (transcript + bản dịch)
```

Với bản `.exe`, app tạo thư mục `VHF_Storage/` bên trong thư mục gốc mà người dùng
đã chọn trong installer. Ví dụ chọn `D:\PRANA_Data` thì audio và kết quả nằm tại
`D:\PRANA_Data\VHF_Storage\`. Khi kiểm thử bằng `run_dev.bat`, dữ liệu source vẫn
nằm tại `VHF\VHF_Storage` và không sử dụng cấu hình của bản đã cài.

---

## Một số cài đặt hay ho

**Ngôn ngữ dịch** — trong file `config/default.toml`:

```toml
[translation]
target_language = "vi"    # vi, en, zh, ja, ko
source_language = "auto"  # tự động phát hiện
```

**AI model** — dùng Gemini 2.5 Flash:

```toml
[gemini]
model = "gemini-2.5-flash"
```

**VAD (Voice Activity Detection)** — phát hiện giọng nói:

```toml
[vad]
backend = "silero"          # silero (AI) hoặc webrtc (nhẹ hơn)
threshold = 0.5              # nhạy hơn nếu giảm (ví dụ 0.3)
min_speech_duration_ms = 300 # bao nhiêu ms thì coi là có người nói
```

---

## Cấu trúc thư mục

```
src/prana_elex/
├── ai/gemini/        # tích hợp Gemini, prompt và xử lý phản hồi
├── app/              # các điểm vào CLI, desktop và bản đóng gói
├── audio/            # thu âm và backend WASAPI/PulseAudio
├── common/           # logger, timing và cấu trúc dữ liệu dùng chung
├── config/           # schema và thiết lập người dùng
├── pipeline/         # điều phối luồng xử lý, sự kiện và session
├── storage/          # lưu cục bộ và Google Cloud Storage
├── ui/               # giao diện desktop, components và dialogs
├── vad/              # phát hiện giọng nói Silero/WebRTC
└── __main__.py       # chạy CLI bằng python -m prana_elex

scripts/
├── dev/                    # launcher dùng khi phát triển
├── packaging/
│   ├── common/             # metadata và validator dùng chung
│   ├── windows/            # spec, hook, build và Inno Setup cho Windows
│   └── linux-arm64/        # spec, build và Debian package cho Pi 4B
└── setup/                  # cài môi trường phát triển Windows/Linux
```

## Yêu cầu

- Windows (WASAPI) hoặc Linux (PulseAudio)
- Google Cloud service-account JSON
- Kết nối internet (để gọi Gemini API)
