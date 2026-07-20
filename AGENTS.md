# Repository Guidelines

## Project Structure & Module Organization

The repository contains a Python 3.11+ desktop/Pi client and two FastAPI services:

- `src/prana_elex/` — client code (audio capture, VAD, storage, backend/auth, and Qt UI).
- `services/prana_api/` and `services/prana_admin/` — public API and IAP-protected admin service.
- `tests/` — suites grouped by `client/`, `api/`, `admin/`, and `packaging/`, plus shared fixtures.
- `config/` — default and platform-specific TOML configuration; `scripts/` — setup, development, and packaging helpers.
- `infra/terraform/` — Google Cloud infrastructure; `docs/` — architecture and operational notes.

Keep new modules under the existing package boundaries and place tests in the matching subsystem directory.

## Build, Test, and Development Commands

Create the local environment with `scripts\setup\setup.bat` (Windows) or `./scripts/setup/setup.sh` (Pi/Linux), then run the client with `run_dev.bat` or `./scripts/dev/run-dev.sh`. Use `scripts\dev\run-cli.bat` (or `run-cli.sh`) for batch transcription.

Run all tests from the repository root:

```bash
python -m pytest
```

Build release artifacts with `buildwin.bat` on Windows or `./buildlinux` on Raspberry Pi. Packaging validation tests exercise the generated layouts; backend development can be started with `uvicorn services.prana_api.main:app --reload --port 8080` after installing that service's requirements.

## Coding Style & Naming Conventions

Follow standard Python style (4-space indentation, clear type hints, and `snake_case` for modules, functions, and variables; `PascalCase` for classes). Use focused modules and preserve the client/API/admin separation. Keep TOML keys lowercase with underscores. Match surrounding code and run the project's available formatter/linter before submitting; avoid drive-by reformatting.

## Testing Guidelines

Tests use `pytest`; files are named `test_*.py` and test functions `test_*`. Add regression coverage beside the affected subsystem, using `tests/fixtures/` for reusable audio or data inputs. Run a targeted test while iterating (for example, `python -m pytest tests/packaging/test_windows_installer.py`) and the full suite before review.

## Commit & Pull Request Guidelines

Use the established Conventional Commit style visible in history, such as `feat(ui): ...`, `refactor(pipeline): ...`, `test: ...`, and `docs: ...`. Keep commits focused and imperative. Pull requests should explain behavior and deployment impact, link relevant issues, list verification commands, and include screenshots or packaging evidence for UI/installer changes. Never commit secrets, credentials, signing keys, or generated release directories.

## Security & Configuration

Treat `config/` values as public client configuration only. Keep Google credentials and service-account material out of the client and repository; use ADC or impersonation for backend development and environment variables for local secrets.
