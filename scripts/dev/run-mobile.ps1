[CmdletBinding()]
param(
    [string]$AvdName = "Prana_API_36",
    [ValidateSet("staging", "production")]
    [string]$Flavor = "staging",
    [int]$BootTimeoutSeconds = 240
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$appRoot = Join-Path $repoRoot "apps\prana_mobile"
$configPath = Join-Path $appRoot "config\$Flavor.json"
$androidSdk = if ($env:ANDROID_SDK_ROOT) {
    $env:ANDROID_SDK_ROOT
} else {
    Join-Path $env:LOCALAPPDATA "Android\Sdk"
}
$adb = Join-Path $androidSdk "platform-tools\adb.exe"
$emulator = Join-Path $androidSdk "emulator\emulator.exe"
$androidStudioJdk = "C:\Program Files\Android\Android Studio\jbr"

$flutterCommand = Get-Command flutter.bat -ErrorAction SilentlyContinue
if (-not $flutterCommand) {
    $fallbackFlutter = Join-Path $env:USERPROFILE "develop\flutter\bin\flutter.bat"
    if (Test-Path -LiteralPath $fallbackFlutter) {
        $flutter = $fallbackFlutter
    } else {
        throw "Không tìm thấy Flutter SDK. Hãy mở terminal mới hoặc thêm Flutter vào PATH."
    }
} else {
    $flutter = $flutterCommand.Source
}

foreach ($requiredPath in @($appRoot, $configPath, $adb, $emulator)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Không tìm thấy: $requiredPath"
    }
}

if (Test-Path -LiteralPath $androidStudioJdk) {
    $env:JAVA_HOME = $androidStudioJdk
    $env:Path = "$(Join-Path $androidStudioJdk 'bin');$env:Path"
}
$env:ANDROID_SDK_ROOT = $androidSdk

function Get-OnlineEmulatorId {
    $line = & $adb devices |
        Where-Object { $_ -match "^(emulator-\d+)\s+device$" } |
        Select-Object -First 1
    if ($line -and $line -match "^(emulator-\d+)") {
        return $Matches[1]
    }
    return $null
}

Write-Host "[PRANA] Kiểm tra Android Emulator..." -ForegroundColor Cyan
& $adb start-server | Out-Null
$deviceId = Get-OnlineEmulatorId

if (-not $deviceId) {
    $offlineEmulator = & $adb devices | Where-Object { $_ -match "^emulator-\d+\s+offline$" }
    if ($offlineEmulator) {
        Write-Host "[PRANA] Dừng phiên emulator bị treo..." -ForegroundColor Yellow
        Get-CimInstance Win32_Process |
            Where-Object {
                $_.Name -in @("emulator.exe", "qemu-system-x86_64.exe") -and
                $_.CommandLine -match [regex]::Escape("@$AvdName")
            } |
            ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Start-Sleep -Seconds 2
        & $adb kill-server | Out-Null
        & $adb start-server | Out-Null
    }

    Write-Host "[PRANA] Mở $AvdName bằng cold boot..." -ForegroundColor Cyan
    Start-Process -FilePath $emulator -ArgumentList "@$AvdName", "-no-snapshot-load"

    $deadline = (Get-Date).AddSeconds($BootTimeoutSeconds)
    do {
        Start-Sleep -Seconds 2
        $deviceId = Get-OnlineEmulatorId
        if ($deviceId) {
            $bootCompleted = (& $adb -s $deviceId shell getprop sys.boot_completed 2>$null).Trim()
            if ($bootCompleted -eq "1") {
                break
            }
        }
    } while ((Get-Date) -lt $deadline)

    if (-not $deviceId -or $bootCompleted -ne "1") {
        throw "Emulator không boot xong sau $BootTimeoutSeconds giây. Hãy kiểm tra Device Manager."
    }
}

Write-Host "[PRANA] Thiết bị sẵn sàng: $deviceId" -ForegroundColor Green
Write-Host "[PRANA] Chạy Flutter $Flavor. Nhấn r để Hot Reload, q để dừng app." -ForegroundColor Cyan

Push-Location $appRoot
try {
    & $flutter run `
        -d $deviceId `
        --flavor $Flavor `
        "--dart-define-from-file=config/$Flavor.json"
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
