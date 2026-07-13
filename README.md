# PRANA ELEX

**Nghe và dịch liên lạc VHF hàng hải** — bắt âm thanh từ thiết bị thu, tự động nhận diện giọng nói, phiên dịch và hiển thị kết quả real-time.

---

## Dành cho người mới bắt đầu

### Bước 1: Cài đặt (làm một lần)

**Windows:**
```cmd
setup.bat
```

**Linux / Raspberry Pi:**
```bash
./setup.sh
```

Script sẽ tự tạo môi trường ảo, cài đặt thư viện, tạo thư mục lưu dữ liệu.

### Bước 2: Nhập API Key

Bạn cần một key của Google Gemini. Đặt nó trước khi chạy app:

```cmd
set GOOGLE_API_KEY=AIzaSy...
```

Hoặc set trong biến môi trường Windows luôn để khỏi phải gõ lại.

### Bước 3: Chạy thôi

**Có giao diện đồ hoạ (GUI):**
```cmd
run_desktop.bat
```

**Chạy trên console (không cần màn hình):**
```cmd
run.bat
```

**Nếu có file WAV muốn xử lý sẵn:**
```cmd
run.bat batch file1.wav file2.wav
```

### Dùng file .exe có sẵn (không cần cài Python)

File `dist\PRANA_ELEX.exe` là bản đóng gói sẵn — copy ra máy khác chạy được luôn:

```cmd
set GOOGLE_API_KEY=AIzaSy...
dist\PRANA_ELEX.exe
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

Mọi thứ được lưu trong thư mục `data/`:

```
data/
├── audio/        ← file WAV từng đoạn hội thoại
└── results/      ← file JSON kết quả (transcript + bản dịch)
```

Mỗi file có tên theo thời gian, dễ tra cứu. Thư mục `data/` đã được git bỏ qua, không sợ lỡ commit.

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
├── app/              # điểm vào: cli, desktop
├── core/             # xử lý chính: audio, config, gemini, pipeline, vad...
├── ui/               # giao diện desktop (PySide6)
└── __main__.py       # chạy từ dòng lệnh: python -m prana_elex
```

## Yêu cầu

- Windows (WASAPI) hoặc Linux (PulseAudio)
- Google Gemini API key
- Kết nối internet (để gọi Gemini API)
