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
    mobile_call = '& (Join-Path $root "run_mobile.bat")'
    assert mobile_call in script
    assert script.index("if ($WithMobile)") < script.index(mobile_call)


def test_private_and_generated_files_are_ignored() -> None:
    gitignore = _read(".gitignore")

    for entry in (
        ".venv/",
        ".secrets/",
        "VHF_Storage/",
        "stations/",
        "*.tfvars",
        "*.apk",
        "*.aab",
        "*.jks",
        "apps/android/config/*.json",
    ):
        assert entry in gitignore
