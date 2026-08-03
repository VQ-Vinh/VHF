[CmdletBinding()]
param(
    [switch]$LocalApi,
    [switch]$WithMobile,
    [string]$AvdName = "Prana_API_36",
    [ValidatePattern("^\d{3,5}x\d{3,5}$")]
    [string]$EmulatorResolution = "1080x2160",
    [ValidateSet("staging", "production")]
    [string]$Flavor = "staging"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$runtimeDir = Join-Path $root ".prana\runtime"
$logDir = Join-Path $root ".prana\logs\dev"
$legacyRuntimeDir = Join-Path $root "VHF_Storage\runtime"
$legacyLogDir = Join-Path $root "VHF_Storage\logs"
$apiPidFile = Join-Path $runtimeDir "api.pid"
$stationPidFile = Join-Path $runtimeDir "station.pid"
$legacyApiPidFile = Join-Path $legacyRuntimeDir "api.pid"
$legacyStationPidFile = Join-Path $legacyRuntimeDir "station.pid"
$cloudApiUrl = "https://prana-api-owuilj5d4a-uc.a.run.app"
$apiHealthUrl = if ($LocalApi) {
    "http://127.0.0.1:8080/health"
} else {
    "$cloudApiUrl/health"
}

New-Item -ItemType Directory -Force -Path $runtimeDir, $logDir | Out-Null
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

function Test-ProcessId {
    param([string]$PidFile)
    if (-not (Test-Path -LiteralPath $PidFile)) {
        return $false
    }
    $savedPid = Get-Content -LiteralPath $PidFile -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if (-not $savedPid) {
        return $false
    }
    return $null -ne (Get-Process -Id $savedPid -ErrorAction SilentlyContinue)
}

function Stop-ManagedProcess {
    param(
        [string]$PidFile,
        [string]$Name
    )
    if (-not (Test-ProcessId $PidFile)) {
        return
    }
    $savedPid = [int](Get-Content -LiteralPath $PidFile | Select-Object -First 1)
    Write-Host "[PRANA] Khoi dong lai $Name (PID $savedPid)..." -ForegroundColor Yellow
    Stop-Process -Id $savedPid -Force
    Wait-Process -Id $savedPid -Timeout 10 -ErrorAction SilentlyContinue
}

function Test-ApiHealth {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $apiHealthUrl -TimeoutSec 2
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Confirm-GoogleAdc {
    $gcloud = Get-Command "gcloud.cmd" -ErrorAction SilentlyContinue
    if (-not $gcloud) {
        $gcloud = Get-Command "gcloud" -ErrorAction SilentlyContinue
    }
    if (-not $gcloud) {
        throw "Khong tim thay gcloud CLI. Cai Google Cloud CLI va chay lai."
    }

    & $gcloud.Source auth application-default print-access-token 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[PRANA] Google ADC da san sang." -ForegroundColor Green
        return
    }

    Write-Host "[PRANA] Google ADC da het han. Dang mo trinh duyet de dang nhap lai..." -ForegroundColor Yellow
    & $gcloud.Source auth application-default login
    if ($LASTEXITCODE -ne 0) {
        throw "Khong the lam moi Google ADC. Chay 'gcloud auth application-default login' roi thu lai."
    }

    & $gcloud.Source auth application-default print-access-token 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Google ADC chua san sang sau khi dang nhap."
    }
    Write-Host "[PRANA] Google ADC da san sang." -ForegroundColor Green
}

function Find-ProcessByCommand {
    param([string]$Pattern)
    try {
        return Get-CimInstance Win32_Process -ErrorAction Stop |
            Where-Object { $_.CommandLine -match $Pattern } |
            Select-Object -First 1
    } catch {
        return $null
    }
}

function Start-LoggedProcess {
    param(
        [string]$FilePath,
        [string[]]$ArgumentList,
        [string]$Name,
        [string]$PidFile
    )
    $stdout = Join-Path $logDir "$Name.stdout.log"
    $stderr = Join-Path $logDir "$Name.stderr.log"
    $process = Start-Process `
        -FilePath $FilePath `
        -ArgumentList $ArgumentList `
        -WorkingDirectory $root `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr `
        -PassThru
    Set-Content -LiteralPath $PidFile -Value $process.Id -Encoding ascii
    Write-Host "[PRANA] Da khoi dong $Name (PID $($process.Id))." -ForegroundColor Green
    Write-Host "        Log: $stdout" -ForegroundColor DarkGray
    return $process
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  PRANA ELEX - Enable Laptop Station + API" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# This is the single development entry point, so restart processes managed by
# an earlier invocation to pick up source/config and refreshed credentials.
if ($LocalApi) {
    # Local backend development accesses Firestore with the developer's ADC.
    # Customer/remote operation never enters this branch.
    Confirm-GoogleAdc
}
Stop-ManagedProcess -PidFile $apiPidFile -Name "API"
Stop-ManagedProcess -PidFile $stationPidFile -Name "Station"
# One-time compatibility for processes started before runtime metadata moved
# out of VHF_Storage. These files can be removed after the old process stops.
Stop-ManagedProcess -PidFile $legacyApiPidFile -Name "legacy API"
Stop-ManagedProcess -PidFile $legacyStationPidFile -Name "legacy Station"

# Preserve old diagnostics while keeping VHF_Storage dedicated to recordings.
if ((Test-Path -LiteralPath $legacyLogDir) -or
    (Test-Path -LiteralPath $legacyRuntimeDir)) {
    $legacyArchive = Join-Path $root (
        ".prana\legacy\" + (Get-Date -Format "yyyyMMdd-HHmmss")
    )
    New-Item -ItemType Directory -Force -Path $legacyArchive | Out-Null
    if (Test-Path -LiteralPath $legacyLogDir) {
        Move-Item -LiteralPath $legacyLogDir -Destination $legacyArchive
    }
    if (Test-Path -LiteralPath $legacyRuntimeDir) {
        Move-Item -LiteralPath $legacyRuntimeDir -Destination $legacyArchive
    }
    Write-Host "[PRANA] Da chuyen log/runtime cu sang $legacyArchive." -ForegroundColor DarkGray
}

if ($LocalApi -and -not (Test-ApiHealth)) {
    $apiPython = Join-Path $root ".venv\backend\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $apiPython)) {
        throw "Khong tim thay backend environment. Can tao .venv\backend truoc."
    }
    $env:PRANA_API_ENVIRONMENT = "development"
    $env:PRANA_API_GOOGLE_CLOUD_PROJECT = "prana-elex-staging-2816"
    $env:PRANA_API_FIREBASE_PROJECT_ID = "prana-elex-staging-2816"
    $env:PRANA_API_STORAGE_BUCKET = "prana-elex-staging-2816-recordings"
    Start-LoggedProcess `
        -FilePath $apiPython `
        -ArgumentList @(
            "-m", "uvicorn", "services.prana_api.main:app",
            "--host", "0.0.0.0", "--port", "8080"
        ) `
        -Name "api" `
        -PidFile $apiPidFile | Out-Null

    Write-Host "[PRANA] Dang cho API khoi dong..." -ForegroundColor Cyan
    $deadline = (Get-Date).AddSeconds(45)
    while (-not (Test-ApiHealth) -and (Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 1
    }
    if (-not (Test-ApiHealth)) {
        throw "API khong san sang. Xem $logDir\api.stderr.log"
    }
    Write-Host "[PRANA] API READY." -ForegroundColor Green
}

$apiMode = if ($LocalApi) { "local development" } else { "Cloud" }
if (-not (Test-ApiHealth)) {
    throw "Khong the ket noi $apiMode API tai $apiHealthUrl."
}
Write-Host "[PRANA] $apiMode API READY: $apiHealthUrl" -ForegroundColor Green

$stationRunning =
    $null -ne (Find-ProcessByCommand "prana_windows[\\/]station|prana_windows\.station")

if ($stationRunning) {
    Write-Host "[PRANA] Laptop Station dang chay." -ForegroundColor Green
} else {
    $stationPython = Join-Path $root ".venv\dev\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $stationPython)) {
        throw "Khong tim thay development environment. Chay scripts\setup\setup.bat."
    }
    $coreSource = Join-Path $root "packages\prana_core\src"
    $windowsSource = Join-Path $root "apps\windows\src"
    $stationConfig = if ($LocalApi) {
        Join-Path $root "apps\windows\config\staging.toml"
    } else {
        Join-Path $root "apps\windows\config\default.toml"
    }
    $env:PYTHONPATH = "$coreSource;$windowsSource"
    Start-LoggedProcess `
        -FilePath $stationPython `
        -ArgumentList @(
            "-m", "prana_windows.station",
            "--config", $stationConfig,
            "--data-dir", $root
        ) `
        -Name "station" `
        -PidFile $stationPidFile | Out-Null
    Start-Sleep -Seconds 2
    if (-not (Test-ProcessId $stationPidFile)) {
        throw "Station dung ngay sau khi khoi dong. Xem $logDir\station.stderr.log"
    }
}

Write-Host "[PRANA] Station dang chay qua $apiMode API." -ForegroundColor Green
Write-Host "[PRANA] Khach hang chi can Internet; khong can gcloud, ADC hay cung Wi-Fi." -ForegroundColor Green

if ($WithMobile) {
    Write-Host "[PRANA] Mo Android Emulator va Flutter $Flavor..." -ForegroundColor Cyan
    Write-Host "[PRANA] API/Station tiep tuc chay nen khi Flutter dung." -ForegroundColor DarkGray
    & (Join-Path $root "run_android_emulator.bat") `
        -AvdName $AvdName `
        -EmulatorResolution $EmulatorResolution `
        -Flavor $Flavor
    exit $LASTEXITCODE
}

Write-Host "[PRANA] Emulator khong duoc khoi dong. Dung -WithMobile khi phat trien Android." -ForegroundColor DarkGray
if (-not $LocalApi) {
    Write-Host "[PRANA] Developer muon chay backend local: enable_station_api.bat -LocalApi" -ForegroundColor DarkGray
}
exit 0
