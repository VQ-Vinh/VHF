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

Khi cài bằng `release/PRANA_ELEX_Setup_1.0.0_x64.exe`, installer sẽ yêu cầu chọn
service-account JSON ở bước **Google Cloud Credentials**. Key được sao chép trong
lúc cài đặt và đường dẫn được ghi vào `settings.json`; key không được nhúng sẵn
trong file Setup.

Khi dùng bản portable trong `dist/PRANA_ELEX/`, tạo cùng cấu trúc bên cạnh file
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

### Dùng file .exe có sẵn (không cần cài Python)

Build sạch toàn bộ ứng dụng bằng một lệnh tại thư mục gốc dự án:

```cmd
build.bat
```

Nếu đã cài Inno Setup 6, lệnh trên đồng thời tạo bộ cài dành cho người dùng:

```text
release/PRANA_ELEX_Setup_1.0.0_x64.exe
```

File `dist\PRANA_ELEX\PRANA_ELEX.exe` là bản đóng gói sẵn — copy ra máy khác chạy được luôn:

```cmd
dist\PRANA_ELEX\PRANA_ELEX.exe
```

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

Với bản `.exe`, `VHF_Storage/` nằm bên trong thư mục lưu mà người dùng đã chọn. Mỗi file có tên theo thời gian, dễ tra cứu; thư mục này đã được Git bỏ qua.

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
├── dev/              # launcher dùng khi phát triển
├── packaging/        # PyInstaller spec, build và runtime hooks
└── setup/            # cài môi trường cho Windows/Linux
```

## Yêu cầu

- Windows (WASAPI) hoặc Linux (PulseAudio)
- Google Gemini API key
- Kết nối internet (để gọi Gemini API)
