from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_windows_setup_creates_station_and_backend_environments() -> None:
    setup = _read("scripts/setup/setup.bat")

    assert r".venv\dev\Scripts\python.exe" in setup
    assert r".venv\backend\Scripts\python.exe" in setup
    assert r"services\prana_api\requirements.txt" in setup
    assert r"services\prana_admin\requirements.txt" in setup
    assert r".venv\dev\Scripts\prana-station-provision.exe" in setup
    assert r".venv\backend\Scripts\uvicorn.exe" in setup


def test_qr_generation_uses_dev_environment_and_private_output() -> None:
    script = _read("generate_station_qr.bat")

    assert r".venv\dev\Scripts\prana-station-provision.exe" in script
    assert 'set "QR_OUTPUT=%PROJECT_ROOT%stations"' in script
    assert r".venv\windows" not in script


def test_enable_station_opens_mobile_only_when_requested() -> None:
    script = _read("scripts/dev/enable-station.ps1")

    assert "[switch]$WithMobile" in script
    assert "if ($WithMobile)" in script
    mobile_call = '& (Join-Path $root "run_android_emulator.bat")'
    assert mobile_call in script
    assert script.index("if ($WithMobile)") < script.index(mobile_call)


def test_enable_station_uses_cloud_without_customer_adc_by_default() -> None:
    script = _read("scripts/dev/enable-station.ps1")

    assert "[switch]$LocalApi" in script
    assert "apps\\windows\\config\\default.toml" in script
    assert "apps\\windows\\config\\staging.toml" in script
    assert "Confirm-GoogleAdc" in script
    local_branch = script.index("if ($LocalApi) {", script.index("Confirm-GoogleAdc"))
    assert local_branch < script.index("Confirm-GoogleAdc", local_branch)


def test_runtime_logs_and_pids_stay_outside_recording_storage() -> None:
    script = _read("scripts/dev/enable-station.ps1")

    assert 'Join-Path $root ".prana\\runtime"' in script
    assert 'Join-Path $root ".prana\\logs\\dev"' in script
    assert 'Join-Path $root "VHF_Storage\\logs\\dev"' not in script
    assert 'Join-Path $root "VHF_Storage\\runtime"' in script  # legacy cleanup only
    assert '".prana\\legacy\\"' in script
    assert "Move-Item -LiteralPath $legacyLogDir" in script
    assert "Move-Item -LiteralPath $legacyRuntimeDir" in script


def test_private_and_generated_files_are_ignored() -> None:
    gitignore = _read(".gitignore")

    for entry in (
        ".venv/",
        ".secrets/",
        "VHF_Storage/",
        ".prana/",
        "stations/",
        "*.tfvars",
        "*.apk",
        "*.aab",
        "*.jks",
        "apps/android/config/*.json",
    ):
        assert entry in gitignore
