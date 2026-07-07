# VHF Radio Processor / Gemini 2.5

Real-time VHF marine radio transcription and translation using Google Gemini 2.5.

## Setup

```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r vhf_processor\requirements.txt
copy .env.example .env
```

Edit `.env` with your `GEMINI_API_KEY` (get from [Google AI Studio](https://aistudio.google.com)).

## Usage

**Real-time:** captures system audio and processes continuously.
```bash
.\run.bat
```

**Batch:** process WAV files.
```bash
.\run.bat batch input.wav
```

**Options:**
- `--list-languages` — show supported languages
- `-t vi` — set target translation language
- `.\run.bat config.toml` — use custom config

## Output

```
[session001 #1] 19:31:55
LANG: VI  |  CONF: 74%
TXT:  Các đài tàu, Đài Thông tin Duyên hải Hồ Chí Minh gọi các đài tàu.
TRN:  All ship stations, Ho Chi Minh Coast Radio calling all ship stations.
! "Người Chi Minh" -> "Hồ Chí Minh"
LATENCY: 11057ms (process: 9823ms | queue: 1234ms)
```

- **TXT** — corrected transcription (read this)
- **TRN** — translation
- **`!`** — model auto-corrected a word
- **CONF** — objective confidence (0-100%)
- **LATENCY** — total time from speech end to result

## Config

Edit `vhf_processor/config/default.toml`:

| Key | Default | Description |
|---|---|---|
| `min_silence_duration_ms` | `1200` | Silence before cutting a segment (ms) |
| `target_language` | `en` | Translation output language |
| `capture_mode` | `loopback` | `loopback`, `device`, or `auto` |
| `model` | `gemini-2.5-flash` | Gemini model |

## Data

All runtime data saved in `data/` (gitignored):
- `data/audio/` — WAV segments
- `data/results/` — JSON results
- `data/logs/` — runtime logs
