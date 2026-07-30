# Repository Guidelines

## Project Structure & Module Organization

The repository contains a Python 3.11+ desktop/Pi client and two FastAPI services:

- `packages/prana_core/src/prana_core/` — platform-neutral pipeline, VAD, storage, backend and station protocol.
- `apps/windows/`, `apps/linux/`, and `apps/android/` — platform composition roots and build assets.
- `services/prana_api/` and `services/prana_admin/` — public API and IAP-protected admin service.
- `tests/` — suites grouped by `core/`, `windows/`, `linux/`, `api/`, `admin/`, and `packaging/`.
- Platform TOML files live beside their app; shared release validators live in `tools/packaging/`.
- `infra/terraform/` — Google Cloud infrastructure; `docs/` — architecture and operational notes.

Keep new modules under the existing package boundaries and place tests in the matching subsystem directory.

## Build, Test, and Development Commands

Create the local environment with `scripts\setup\setup.bat` (Windows) or `./scripts/setup/setup.sh` (Pi/Linux). Use `enable_station_api.bat` to run the Windows Station against the Cloud API; this customer/remote workflow must not require Google Cloud CLI or ADC. Developers may explicitly use `enable_station_api.bat -LocalApi` when testing the backend locally, which is the only mode that may require ADC. Use `run_android_emulator.bat` for Flutter development, and `scripts\dev\run-cli.bat` (or `run-cli.sh`) for batch transcription.

Run all tests from the repository root:

```bash
python -m pytest
```

Build an Android APK for a physical phone with `build_android_apk.bat`, or a Linux artifact with `./buildlinux`. Platform-specific Windows build logic remains under `apps/windows/` but has no root wrapper while Android is the active development target. Packaging validation tests exercise the generated layouts; backend development can be started with `uvicorn services.prana_api.main:app --reload --port 8080` after installing that service's requirements.

Do not automatically build an APK after routine Android source or UI changes. During normal iteration, run formatting, static analysis, and targeted tests only. Build an APK only when the user explicitly requests it, when APK/release packaging is the task itself, or when a Gradle/package/device-only issue cannot be validated by lighter checks. Do not rebuild merely to provide a fresh artifact after every edit.

## Coding Style & Naming Conventions

Follow standard Python style (4-space indentation, clear type hints, and `snake_case` for modules, functions, and variables; `PascalCase` for classes). Use focused modules and preserve the client/API/admin separation. Keep TOML keys lowercase with underscores. Match surrounding code and run the project's available formatter/linter before submitting; avoid drive-by reformatting.

## Testing Guidelines

Tests use `pytest`; files are named `test_*.py` and test functions `test_*`. Add regression coverage beside the affected subsystem, using `tests/fixtures/` for reusable audio or data inputs. Run a targeted test while iterating (for example, `python -m pytest tests/packaging/test_windows_installer.py`) and the full suite before review.

## Commit & Pull Request Guidelines

Use the established Conventional Commit style visible in history, such as `feat(ui): ...`, `refactor(pipeline): ...`, `test: ...`, and `docs: ...`. Keep commits focused and imperative.

When the user asks to commit and push, split the working changes into multiple logical commits instead of creating one broad commit. Group changes by independently reviewable concern, for example implementation, tests, documentation, infrastructure, or an unrelated bug fix. Keep tightly coupled code and its required regression test together when separating them would leave an invalid or misleading commit. Before pushing, review the staged file list and diff for each group, use a Conventional Commit message that describes that group, and push only after all intended commits have been created and verified.

Pull requests should explain behavior and deployment impact, link relevant issues, list verification commands, and include screenshots or packaging evidence for UI/installer changes. Never commit secrets, credentials, signing keys, or generated release directories.

## Security & Configuration

Treat platform app config values as public client configuration only. Keep Google credentials and service-account material out of the client and repository; use ADC or impersonation for backend development and environment variables for local secrets.
