# Repository Guidelines

## Project Structure & Module Organization

The repository contains a Python 3.11+ desktop/Pi client and two FastAPI services:

- `packages/prana_core/src/prana_core/` — platform-neutral pipeline, VAD, storage, backend and station protocol.
- `apps/windows/`, `apps/linux/`, and `apps/android/` — platform composition roots and build assets.
- `services/prana_api/` and `services/prana_admin/` — public API and IAP-protected admin service.
- `tests/` — suites grouped by `core/`, `windows/`, `linux/`, `api/`, `admin/`, `packaging/`, and `conventions/`. `packaging/` exercises the release tooling and the artifacts it produces; `conventions/` reads tracked files as text to pin repository rules that no runtime check would catch.
- Platform TOML files live beside their app; shared release validators live in `tools/packaging/`. The Windows configs commit a Firebase Web API key because the desktop app signs users in and that key is public by design; the Linux station signs nobody in and ships it empty, and the Android config is generated per build and stays out of git. Each config carries a comment saying so.
- `infra/terraform/` — Google Cloud infrastructure; `docs/` — architecture and operational notes.

Keep new modules under the existing package boundaries and place tests in the matching subsystem directory.

## Build, Test, and Development Commands

Create the local environment with `scripts\setup\setup.bat` (Windows) or `./scripts/setup/setup.sh` (Pi/Linux). Use `enable_station_api.bat` to run the Windows Station against the Cloud API; this customer/remote workflow must not require Google Cloud CLI or ADC. Developers may explicitly use `enable_station_api.bat -LocalApi` when testing the backend locally, which is the only mode that may require ADC. Use `run_android_emulator.bat` for Flutter development, and `scripts\dev\run-cli.bat` (or `run-cli.sh`) for batch transcription.

Run tests from the repository root, but not all of them in one environment --
no environment has every dependency, and CI does not either. It splits the same
way, one job per group:

```bash
# API and Admin: needs both services' requirements (.venv/backend)
python -m pytest tests/api tests/admin

# Core, Station and repo rules: needs prana_core and apps/linux (.venv/dev)
python -m pytest tests/core tests/linux tests/packaging tests/conventions

# Windows desktop: needs prana_core and apps/windows
python -m pytest tests/windows
```

A bare `python -m pytest` fails at collection with `ModuleNotFoundError`, which
looks like a broken checkout and is not one. When you add a suite directory,
add it to the matching job in `.github/workflows/ci.yml`; a test in
`tests/conventions/` fails if you forget.

GitHub Actions owns the required `CI / gate` check. A merge to `main` may
automatically deploy only the changed API/Admin service to staging after that
check succeeds. Do not bypass the gate or manually deploy a different image
over a CI-managed staging revision unless performing a documented rollback.
Terraform apply, Android release, and production promotion require their
protected GitHub Environment approvals. CI/CD authentication must use GitHub
OIDC Workload Identity Federation; never add a service-account JSON key.

Build an Android APK for a physical phone with `build_android_apk.bat`, or a Linux artifact with `./buildlinux`. Platform-specific Windows build logic remains under `apps/windows/` but has no root wrapper while Android is the active development target. Packaging validation tests exercise the generated layouts; backend development can be started with `uvicorn services.prana_api.main:app --reload --port 8080` after installing that service's requirements.

Do not automatically build an APK after routine Android source or UI changes. During normal iteration, run formatting, static analysis, and targeted tests only. Build an APK only when the user explicitly requests it, when APK/release packaging is the task itself, or when a Gradle/package/device-only issue cannot be validated by lighter checks. Do not rebuild merely to provide a fresh artifact after every edit.

## Coding Style & Naming Conventions

Follow standard Python style (4-space indentation, clear type hints, and `snake_case` for modules, functions, and variables; `PascalCase` for classes). Use focused modules and preserve the client/API/admin separation. Keep TOML keys lowercase with underscores. Match surrounding code and run the project's available formatter/linter before submitting; avoid drive-by reformatting.

## Testing Guidelines

Tests use `pytest`; files are named `test_*.py` and test functions `test_*`. Add regression coverage beside the affected subsystem, using `tests/fixtures/` for reusable audio or data inputs. Run a targeted test while iterating (for example, `python -m pytest tests/packaging/test_windows_installer.py`) and the full suite before review.

## Raspberry Pi RX Audio Capture

Raspberry Pi RX must capture through ALSA using `arecord`, not through a
PyAudio/PortAudio input callback. On the validated Pi and USB SoundCard,
PortAudio reported `paInputOverflow` on almost every callback and delivered
only about 4.7 seconds of PCM during a 15-second recording. Direct
`arecord -D hw:<card>,<device>` capture retained the complete audio.

Keep the platform boundary as follows:

- Windows capture uses the WASAPI adapter.
- Linux/Raspberry Pi capture uses an `arecord` subprocess with raw mono PCM16;
  resolve the ALSA hardware identity from the selected device instead of
  relying on the system default input.
- The capture reader only emits ordered PCM frames into the core capture
  queue. VAD, segmentation, resampling, storage, and Cloud processing remain
  in `prana_core` and must not run on the real-time capture callback/thread.
- Log and surface an unexpected `arecord` exit. Do not silently fall back to a
  PortAudio callback on Raspberry Pi.

The confirmed RX baseline for the current Raspberry Pi installation is a Mic
Capture level of `18/28` (approximately `+15 dB`),
`min_silence_duration_ms = 1500`, and
`max_segment_duration_ms = 15000`. Persist mixer changes with `alsactl store`.
Treat capture gain as hardware-specific: verify it with a raw `arecord` sample
and clipping measurements before changing this baseline.

When diagnosing Pi RX quality, first compare a raw `arecord` WAV with the
Station-produced WAV. If raw capture is clear but Station audio is incomplete,
inspect the Linux capture adapter and frame continuity before tuning VAD or
changing Android/API playback.

## Raspberry Pi TX and PTT Safety

Raspberry Pi TX uses BCM GPIO17 active-high when `[ptt].enabled = true`; the
shared default remains disabled so Windows/Laptop Stations use manual PTT. A Pi
GPIO initialization failure must not stop RX or heartbeat, but it must publish
`ptt_ready=false` and prevent TX claim. Never silently fall back to playback
without PTT on a Pi configured for GPIO control.

The required TX order is: pause RX capture, assert PTT, wait 400 ms key-up, play
the final WAV, wait 300 ms tail, release PTT, then resume RX only when desired
state is still running. Final WAV duration is limited to 120 seconds and the
independent absolute watchdog is 122 seconds. All error, shutdown, SIGTERM and
player-hang paths must release PTT. Failed TX is never replayed automatically.

Use a dummy load or LED to validate GPIO timing and the hung-player watchdog
before connecting the VHF PTT circuit. Channel-busy sensing is not implemented.

## Commit & Pull Request Guidelines

Use the established Conventional Commit style visible in history, such as `feat(ui): ...`, `refactor(pipeline): ...`, `test: ...`, and `docs: ...`. Keep commits focused and imperative.

When the user asks to commit and push, split the working changes into multiple logical commits instead of creating one broad commit. Group changes by independently reviewable concern, for example implementation, tests, documentation, infrastructure, or an unrelated bug fix. Keep tightly coupled code and its required regression test together when separating them would leave an invalid or misleading commit. Before pushing, review the staged file list and diff for each group, use a Conventional Commit message that describes that group, and push only after all intended commits have been created and verified.

Pull requests should explain behavior and deployment impact, link relevant issues, list verification commands, and include screenshots or packaging evidence for UI/installer changes. Never commit secrets, credentials, signing keys, or generated release directories.

## Security & Configuration

Treat platform app config values as public client configuration only. Keep Google credentials and service-account material out of the client and repository; use ADC or impersonation for backend development and environment variables for local secrets.
