# Troubleshooting PRANA ELEX

Bắt đầu từ lớp gần phần cứng nhất rồi mới thay đổi pipeline hoặc VAD. Xem log và
trạng thái thực tế trước khi restart hoặc chỉnh cấu hình.

## App không thấy Station online

- Kiểm tra Internet trên App và Station.
- Kiểm tra service/process Station và heartbeat mới nhất.
- Android và Station không cần cùng Wi-Fi.
- Raspberry Pi:

  ```bash
  systemctl status prana-station --no-pager
  sudo journalctl -u prana-station -n 100 --no-pager
  ```

## START mắc ở “Đang bật”

- Kiểm tra USB SoundCard bằng `arecord -l` trên Pi hoặc danh sách device Windows.
- Mở **Cài đặt Station**, quét lại và chọn input có capture channel.
- Nếu Station báo `AUDIO_INPUT_DEVICE_NOT_FOUND`, kết nối input rồi nhấn
  **Thử lại** hoặc **Dừng**.
- Nếu cắm USB-SC sau khi service Pi đã chạy nhưng Scan vẫn rỗng, kiểm tra log và
  restart `prana-station` để PortAudio khởi tạo lại danh sách thiết bị.

## Raspberry Pi không thấy USB SoundCard

Kiểm tra theo thứ tự USB → ALSA → quyền service:

```bash
lsusb
cat /proc/asound/cards
arecord -l
aplay -l
sudo -u prana-elex arecord -l
```

Card đã kiểm chứng thường xuất hiện dưới dạng `USB Audio Device`; card index có
thể thay đổi sau reboot hoặc khi cắm thêm thiết bị.

Thu WAV raw để xác nhận phần cứng trước khi chạy pipeline:

```bash
arecord -D hw:CARD=Device,DEV=0 \
  -t wav -f S16_LE -c 1 -r 44100 -d 10 rx-test.wav
```

Nếu `CARD=Device` không tồn tại, dùng card/device do `arecord -l` trả về.

## Raspberry Pi RX đứt đoạn hoặc nghẹt

Raspberry Pi phải capture trực tiếp bằng ALSA/`arecord`, không dùng callback
PyAudio/PortAudio cho luồng realtime.

1. Xác nhận process capture:

   ```bash
   ps -ef | grep arecord
   ```

2. Thu và nghe WAV raw trước khi chỉnh VAD.
3. So sánh WAV raw với WAV trong `VHF_Storage/RX/audio`.
4. Nếu raw rõ nhưng Station thiếu audio, kiểm tra Linux capture adapter và tính
   liên tục của frame.
5. Chỉ thay gain sau khi đo clipping.

Baseline đã kiểm chứng cho USB SoundCard hiện tại:

```text
Mic Capture: +15 dB (18/28)
min_silence_duration_ms: 1500
max_segment_duration_ms: 15000
```

Đặt và lưu gain khi cần:

```bash
amixer -c 3 cset name='Mic Capture Volume' 18
sudo alsactl store 3
```

Dùng `amixer -c <card>` nếu USB-SC không còn là card 3.

## TX dịch được nhưng không phát

- Station phải online và đã START.
- Kiểm tra `TX OUTPUT` có output channel.
- Trên Pi có GPIO PTT, xác nhận `ptt_ready=true`; không fallback sang phát không
  PTT khi GPIO được cấu hình nhưng lỗi.
- Kiểm tra job đang ở `synthesizing`, `queued`, `transmitting` hay `failed`.
- Job lỗi không tự replay; retry thủ công sau khi sửa Station/output.
- Dùng tải giả hoặc LED để kiểm tra GPIO17 và watchdog trước khi nối mạch VHF.

## Android không nhận Hot Reload

Trong terminal `flutter run`, nhấn `r`. Dùng Hot Restart (`R`) hoặc chạy lại App
khi thay native manifest, Gradle, permission hoặc plugin.

Kiểm tra điện thoại kết nối ADB:

```powershell
& "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" devices -l
```

## Vị trí log

Windows development:

```text
.prana/logs/dev/api.stdout.log
.prana/logs/dev/api.stderr.log
.prana/logs/dev/station.stdout.log
.prana/logs/dev/station.stderr.log
```

Raspberry Pi:

```bash
sudo journalctl -u prana-station -f
```
