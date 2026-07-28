[CmdletBinding()]
param(
    [string]$AvdName = "Prana_API_36",
    [ValidatePattern("^\d{3,5}x\d{3,5}$")]
    [string]$EmulatorResolution = "1080x2160",
    [ValidateSet("staging", "production")]
    [string]$Flavor = "staging",
    [int]$BootTimeoutSeconds = 240
)

$ErrorActionPreference = "Stop"
$utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::InputEncoding = $utf8
[Console]::OutputEncoding = $utf8
$OutputEncoding = $utf8

$appRoot = Split-Path -Parent $PSScriptRoot
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
$prebuiltApk = Join-Path $appRoot "build\app\outputs\flutter-apk\app-$Flavor-debug.apk"

function Get-EmulatorAvdName {
    param([string]$DeviceId)
    $name = (& $adb -s $DeviceId shell getprop ro.boot.qemu.avd_name 2>$null).Trim()
    if (-not $name) {
        $name = & $adb -s $DeviceId emu avd name 2>$null |
            Where-Object { $_ -and $_ -notmatch "^OK$" } |
            Select-Object -First 1
    }
    if ($name) {
        return $name.Trim()
    }
    return $null
}

function Get-OnlineEmulatorId {
    $lines = & $adb devices |
        Where-Object { $_ -match "^(emulator-\d+)\s+device$" }
    foreach ($line in $lines) {
        if ($line -match "^(emulator-\d+)") {
            $candidateId = $Matches[1]
            if ((Get-EmulatorAvdName -DeviceId $candidateId) -eq $AvdName) {
                return $candidateId
            }
        }
    }
    return $null
}

function Get-EmulatorResolution {
    param([string]$DeviceId)
    $sizeLines = & $adb -s $DeviceId shell wm size 2>$null
    $effectiveSize = $sizeLines |
        Where-Object { $_ -match "^Override size:\s*(\d+x\d+)$" } |
        Select-Object -Last 1
    if (-not $effectiveSize) {
        $effectiveSize = $sizeLines |
            Where-Object { $_ -match "^Physical size:\s*(\d+x\d+)$" } |
            Select-Object -Last 1
    }
    if ($effectiveSize -and $effectiveSize -match "(\d+x\d+)") {
        return $Matches[1]
    }
    return $null
}

Write-Host "[PRANA] Chuẩn bị APK debug trước khi mở Emulator..." -ForegroundColor Cyan
Push-Location $appRoot
try {
    & $flutter build apk `
        --debug `
        --flavor $Flavor `
        "--dart-define-from-file=config/$Flavor.json"
    if ($LASTEXITCODE -ne 0) {
        throw "Không thể build APK $Flavor cho Emulator."
    }
} finally {
    Pop-Location
}
if (-not (Test-Path -LiteralPath $prebuiltApk)) {
    throw "Flutter báo build thành công nhưng không tìm thấy APK: $prebuiltApk"
}

Write-Host "[PRANA] Kiểm tra Android Emulator..." -ForegroundColor Cyan
& $adb start-server | Out-Null
$deviceId = Get-OnlineEmulatorId

if ($deviceId) {
    $currentResolution = Get-EmulatorResolution -DeviceId $deviceId
    if ($currentResolution -ne $EmulatorResolution) {
        Write-Host (
            "[PRANA] Restarting $AvdName to resize " +
            "$currentResolution -> $EmulatorResolution..."
        ) -ForegroundColor Yellow
        & $adb -s $deviceId emu kill | Out-Null
        $deadline = (Get-Date).AddSeconds(20)
        do {
            Start-Sleep -Milliseconds 500
        } while (
            (Get-OnlineEmulatorId) -and
            (Get-Date) -lt $deadline
        )
        $deviceId = $null
    }
}

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
    Start-Process `
        -FilePath $emulator `
        -ArgumentList "@$AvdName", "-no-snapshot-load", "-skin", $EmulatorResolution

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
for ($stableCheck = 1; $stableCheck -le 3; $stableCheck++) {
    Start-Sleep -Seconds 2
    if ((Get-OnlineEmulatorId) -ne $deviceId) {
        throw (
            "Emulator bị ngắt khỏi ADB ngay sau khi boot. " +
            "Hãy đóng ứng dụng nặng hoặc giảm RAM của AVD rồi chạy lại."
        )
    }
}
Write-Host "[PRANA] Chạy Flutter $Flavor. Nhấn r để Hot Reload, q để dừng app." -ForegroundColor Cyan

Push-Location $appRoot
try {
    & $flutter run `
        -d $deviceId `
        --flavor $Flavor `
        "--use-application-binary=$prebuiltApk" `
        "--dart-define-from-file=config/$Flavor.json"
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
