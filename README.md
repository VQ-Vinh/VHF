# VHF Radio Processor / Gemini 2.5

Real-time VHF marine radio transcription and translation using Google Gemini 2.5.

Captures audio from a USB SoundCard (or any input device), detects speech via Silero VAD, transcribes and translates using Gemini, then saves results locally and optionally uploads to Google Cloud Storage.

## Quick Start

### 1. Setup (one-time)

**Windows:**
```cmd
setup.bat
```

**Linux / Raspberry Pi:**
```bash
./setup.sh
```

The setup script will:
- Check Python 3.11+
- Create a virtual environment (`venv/`)
- Install all dependencies
- Create `data/` directories

### 2. Run

**Real-time mode** (captures from audio device and processes continuously):

```cmd
run.bat
```

**Batch mode** (process existing WAV files):

```cmd
run.bat batch input.wav
```

**Options:**

| Flag | Example | Description |
|---|---|---|
| `-t` | `run.bat -t vi` | Set target translation language |
| `--list-languages` | `run.bat --list-languages` | Show supported languages |
| config path | `run.bat config.toml` | Use a custom config file |

## Audio Device Setup

The program captures from an audio input device (USB SoundCard, line-in, microphone).

First-time users should list available devices:

```cmd
run.bat --list-devices
```

Or manually check using Python:

```python
import pyaudiowpatch as pyaudio
pa = pyaudio.PyAudio()
for i in range(pa.get_device_count()):
    info = pa.get_device_info_by_index(i)
    print(f'[{i}] {info["name"]} | inputs={info["maxInputChannels"]} | sr={info["defaultSampleRate"]}')
pa.terminate()
```

Set the correct device index in `vhf_processor/config/default.toml`:

```toml
[audio]
capture_mode = "device"
device_index = 17          # ← change to your device index
```

## Output

```
------------------------------------------------------------
  [#1] 19:31:55
  LANG: VI  |  CONF: 74%
  TXT:  Các đài tàu, Đài Thông tin Duyên hải Hồ Chí Minh gọi các đài tàu.
  TRN:  All ship stations, Ho Chi Minh Coast Radio calling all ship stations.
  ! "Người Chi Minh" -> "Hồ Chí Minh"
  LATENCY: 11057ms (process: 9823ms | queue: 1234ms)
------------------------------------------------------------
```

| Field | Description |
|---|---|
| **TXT** | Restored transcription with punctuation |
| **TRN** | Translation to target language |
| **!** | Model auto-corrected a word (raw → restored) |
| **CONF** | Objective confidence score (0-100%) from token logprobs |
| **LATENCY** | Total time from speech end to result |

## Configuration

Edit `vhf_processor/config/default.toml` (or use a custom config file).

### Audio

| Key | Default | Description |
|---|---|---|
| `capture_mode` | `"device"` | `"device"`=input device, `"loopback"`=system audio, `"auto"`=try loopback first |
| `sample_rate` | `48000` | Auto-detected from device (this is fallback) |
| `channels` | `1` | Mono capture |
| `frame_size` | `2048` | Samples per callback (~43ms @ 48kHz) |
| `device_index` | `17` | Audio input device index (`-1` for auto) |

### Voice Activity Detection (VAD)

| Key | Default | Description |
|---|---|---|
| `backend` | `"silero"` | `"silero"` (AI) or `"webrtc"` (lightweight) |
| `min_speech_duration_ms` | `300` | Minimum speech before segment is valid |
| `min_silence_duration_ms` | `1200` | Silence duration before cutting a segment |
| `threshold` | `0.5` | VAD sensitivity (lower = more sensitive) |
| `energy_threshold` | `500` | Pre-filter RMS energy (skip VAD for silence) |

### Gemini

| Key | Default | Description |
|---|---|---|
| `model` | `"gemini-2.5-flash"` | Gemini model to use |
| `timeout_seconds` | `30` | API timeout |
| `max_retries` | `3` | Retry count on failure |

### Translation

| Key | Default | Description |
|---|---|---|
| `target_language` | `"en"` | Output language (vi, en, zh, ja, ko) |
| `source_language` | `"auto"` | `"auto"` for automatic detection |

### Storage

| Key | Default | Description |
|---|---|---|
| `storage.gcs.enabled` | `true` | Upload audio + JSON to GCS |
| `storage.gcs.bucket_name` | `"vhf-recordings"` | GCS bucket name |
| `storage.retention_days` | `14` | Auto-delete files older than N days |
| `storage.cleanup_interval_hours` | `24` | Cleanup check frequency |

## Preset Configs

The `vhf_processor/config/` directory includes ready-to-use presets:

| File | Platform | Notes |
|---|---|---|
| `default.toml` | Windows | USB SoundCard, device_index=17, GCS enabled |
| `rpi.toml` | Raspberry Pi | Auto device, lower VAD threshold, GCS enabled |
| `windows-device.toml` | Windows | Device capture, GCS disabled |

Use a preset with:

```cmd
run.bat vhf_processor/config/rpi.toml
```

## Data

**Local** — all runtime data saved in `data/` (gitignored):
```
data/
├── audio/        ← WAV segments (YYYYMMDD_HHMMSS_0001.wav)
└── results/      ← JSON results (YYYYMMDD_HHMMSS_0001.json)
```

**GCS** — when `storage.gcs.enabled = true`:
```
gs://vhf-recordings/audio/YYYY/MM/DD/
gs://vhf-recordings/results/YYYY/MM/DD/
```

**Auto-cleanup:** Files older than `retention_days` are deleted from both local and GCS at startup and every `cleanup_interval_hours` thereafter.

## Architecture

```
USB SoundCard
    ↓ (PCM audio via WASAPI/PulseAudio)
AudioRecorder → callback → VAD (Silero)
    ↓ speech segment detected
PipelineOrchestrator (thread pool)
    ├── Normalize gain
    ├── Resample to 16kHz
    ├── Trim trailing silence
    ├── Save WAV (local)
    └── Gemini API → JSON result
         ├── Print to console
         ├── Save JSON (local)
         └── Upload WAV + JSON (GCS)
```

## Requirements

- Python 3.11+
- Windows (WASAPI) or Linux (PulseAudio)
- Google Gemini API key
- Internet connection (for Gemini API + optional GCS)

See `pyproject.toml` for full dependency list.
