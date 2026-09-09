"""Exercise native stderr handling in the Windows PowerShell used by run.bat."""

import os
from pathlib import Path
import subprocess

import pytest


@pytest.mark.skipif(os.name != "nt", reason="Windows PowerShell native stderr semantics")
def test_adb_probes_tolerate_closed_transport_and_wait_for_offline_serial(tmp_path):
    adb = tmp_path / "adb.cmd"
    adb.write_text(
        "@echo off\n"
        'if "%PRANA_TEST_MODE%"=="failed" goto failed\n'
        'if "%1"=="devices" goto devices\n'
        'if "%PRANA_TEST_MODE%"=="closing" goto failed\n'
        'if "%PRANA_TEST_MODE%"=="fallback" (\n'
        '  if "%3"=="shell" goto failed\n'
        "  echo Prana_API_36\n  echo OK\n  exit /b 0\n)\n"
        'if "%4"=="wm" (\n'
        "  echo Physical size: 1080x2400\n"
        "  echo Override size: 1080x2160\n  exit /b 0\n)\n"
        "echo Prana_API_36\nexit /b 0\n"
        ":devices\necho List of devices attached\n"
        'if "%PRANA_TEST_MODE%"=="offline" echo emulator-5554 offline\n'
        'if "%PRANA_TEST_MODE%"=="healthy" echo emulator-5554 device\n'
        'if "%PRANA_TEST_MODE%"=="closing" echo emulator-5554 device\n'
        "exit /b 0\n"
        ":failed\necho stale-output\necho error: closed 1>&2\nexit /b 1\n",
        encoding="ascii",
    )
    harness = tmp_path / "probe.ps1"
    harness.write_text(
        r"""param($Runner, $AdbPath)
$ErrorActionPreference = 'Stop'
$adb = $AdbPath
$AvdName = 'Prana_API_36'
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($Runner, [ref]$tokens, [ref]$errors)
if ($errors.Count) { throw $errors[0] }
$ast.FindAll({ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] }, $false) |
    ForEach-Object { Invoke-Expression $_.Extent.Text }
$env:PRANA_TEST_MODE = 'failed'
if ($null -ne (Get-EmulatorAvdName 'emulator-5554')) { throw 'Failed name probe leaked output' }
if ($null -ne (Get-EmulatorResolution 'emulator-5554')) { throw 'Failed size probe leaked output' }
if (-not (Test-AdbDevicePresent 'emulator-5554')) { throw 'Server failure cannot prove exit' }
if ($ErrorActionPreference -ne 'Stop') { throw 'Probe changed caller error policy' }
$env:PRANA_TEST_MODE = 'fallback'
if ((Get-EmulatorAvdName 'emulator-5554') -ne $AvdName) { throw 'AVD console fallback failed' }
$env:PRANA_TEST_MODE = 'offline'
if (-not (Test-AdbDevicePresent 'emulator-5554')) { throw 'Offline serial must still be awaited' }
if ($null -ne (Get-OnlineEmulatorId)) { throw 'Offline serial reported ready' }
$env:PRANA_TEST_MODE = 'closing'
if (-not (Test-AdbDevicePresent 'emulator-5554')) { throw 'Closing serial must still be awaited' }
if ($null -ne (Get-OnlineEmulatorId)) { throw 'Closed transport reported ready' }
$env:PRANA_TEST_MODE = 'gone'
if (Test-AdbDevicePresent 'emulator-5554') { throw 'Removed serial still present' }
$env:PRANA_TEST_MODE = 'healthy'
if ((Get-OnlineEmulatorId) -ne 'emulator-5554') { throw 'Healthy AVD not recognized' }
if ((Get-EmulatorResolution 'emulator-5554') -ne '1080x2160') { throw 'Override resolution lost' }
Write-Output 'PASS'
""",
        encoding="utf-8-sig",
    )
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(harness),
            str(Path("apps/android/scripts/run.ps1").resolve()),
            str(adb),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout
