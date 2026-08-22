[CmdletBinding()]
param(
    [ValidateSet("staging", "production")]
    [string]$Flavor = "staging",

    [ValidateSet("auto", "debug", "release")]
    [string]$BuildMode = "auto",

    # Install this exact file instead of searching the build outputs.
    [string]$Apk = "",

    # Serial from `adb devices`. Required only when several devices are attached.
    [string]$Device = "",

    [switch]$Build,

    [switch]$Launch
)

$ErrorActionPreference = "Stop"

# A plain message beats a PowerShell stack trace for whoever runs the .bat.
function Fail([string]$message) {
    Write-Host ""
    Write-Host "[PRANA] LOI: $message" -ForegroundColor Red
    exit 1
}

$appRoot = Split-Path -Parent $PSScriptRoot
$repoRoot = Split-Path -Parent (Split-Path -Parent $appRoot)
$resolvedMode = if ($BuildMode -eq "auto") {
    if ($Flavor -eq "production") { "release" } else { "debug" }
} else {
    $BuildMode
}

function Resolve-Adb {
    $command = Get-Command adb.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }

    $roots = @($env:ANDROID_SDK_ROOT, $env:ANDROID_HOME, (Join-Path $env:LOCALAPPDATA "Android\Sdk"))
    foreach ($root in $roots) {
        if (-not $root) { continue }
        $candidate = Join-Path $root "platform-tools\adb.exe"
        if (Test-Path -LiteralPath $candidate) { return $candidate }
    }
    Fail "Khong tim thay adb.exe. Cai Android SDK Platform-Tools hoac them vao PATH."
}

# `adb devices` prints a header line and a blank tail; keep the tab-separated rows.
function Get-AttachedDevices([string]$adb) {
    $rows = & $adb devices | Select-Object -Skip 1 | Where-Object { $_ -match "\t" }
    return $rows | ForEach-Object {
        $parts = $_ -split "\t"
        [pscustomobject]@{ Serial = $parts[0].Trim(); State = $parts[1].Trim() }
    }
}

$adb = Resolve-Adb
Write-Host "[PRANA] adb: $adb" -ForegroundColor Cyan

if ($Build) {
    Write-Host "[PRANA] Build truoc khi cai..." -ForegroundColor Cyan
    & (Join-Path $PSScriptRoot "build-apk.ps1") -Flavor $Flavor -BuildMode $BuildMode
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($Apk) {
    if (-not (Test-Path -LiteralPath $Apk)) { Fail "Khong tim thay APK: $Apk" }
    $apkFile = Get-Item -LiteralPath $Apk
} else {
    # build-apk.ps1 writes the first two; a bare `flutter build apk` writes the third.
    $candidates = @(
        (Join-Path $repoRoot "installers\android\$Flavor\prana-elex-$Flavor-$resolvedMode.apk"),
        (Join-Path $repoRoot "build\buildapp\flutter\app\outputs\flutter-apk\app-$Flavor-$resolvedMode.apk"),
        (Join-Path $appRoot "build\app\outputs\flutter-apk\app-$Flavor-$resolvedMode.apk")
    )
    $apkFile = $candidates |
        Where-Object { Test-Path -LiteralPath $_ } |
        ForEach-Object { Get-Item -LiteralPath $_ } |
        Sort-Object LastWriteTimeUtc -Descending |
        Select-Object -First 1
    if (-not $apkFile) {
        Write-Host "[PRANA] Da tim o:" -ForegroundColor Yellow
        $candidates | ForEach-Object { Write-Host "         $_" -ForegroundColor Yellow }
        Fail "Chua co APK $Flavor-$resolvedMode. Chay lai voi -Build, hoac build_android_apk.bat truoc."
    }
}

$builtAt = $apkFile.LastWriteTime.ToString("yyyy-MM-dd HH:mm")
$sizeMb = [math]::Round($apkFile.Length / 1MB, 2)
Write-Host "[PRANA] APK: $($apkFile.FullName)" -ForegroundColor Cyan
Write-Host "[PRANA] Build luc $builtAt | $sizeMb MB" -ForegroundColor Cyan

$devices = @(Get-AttachedDevices $adb)
$unauthorized = @($devices | Where-Object { $_.State -eq "unauthorized" })
if ($unauthorized.Count -gt 0) {
    Write-Host "[PRANA] May dang cho cap quyen: $($unauthorized.Serial -join ', ')" -ForegroundColor Yellow
    Fail "Mo khoa dien thoai va bam 'Cho phep' o hop thoai 'Cho phep go loi USB', roi chay lai."
}

$ready = @($devices | Where-Object { $_.State -eq "device" })
if ($ready.Count -eq 0) {
    Fail "Khong co thiet bi nao. Cam cap USB (cap truyen du lieu), bat 'Go loi USB' trong Tuy chon nha phat trien."
}
if ($Device) {
    if ($ready.Serial -notcontains $Device) {
        Fail "Khong thay thiet bi '$Device'. Dang co: $($ready.Serial -join ', ')"
    }
    $target = $Device
} elseif ($ready.Count -gt 1) {
    Write-Host "[PRANA] Co nhieu thiet bi:" -ForegroundColor Yellow
    $ready | ForEach-Object { Write-Host "         $($_.Serial)" -ForegroundColor Yellow }
    Fail "Chon mot may bang -Device <serial>."
} else {
    $target = $ready[0].Serial
}

$model = (& $adb -s $target shell getprop ro.product.model).Trim()
Write-Host "[PRANA] Thiet bi: $target ($model)" -ForegroundColor Cyan

$package = if ($Flavor -eq "staging") { "com.dlv.prana_mobile.staging" } else { "com.dlv.prana_mobile" }

# -r keeps app data, -d allows reinstalling over a build with the same version.
Write-Host "[PRANA] Dang cai..." -ForegroundColor Cyan
& $adb -s $target install -r -d $apkFile.FullName
if ($LASTEXITCODE -ne 0) {
    Write-Host "[PRANA] Neu bao INSTALL_FAILED_UPDATE_INCOMPATIBLE thi ban da cai" -ForegroundColor Yellow
    Write-Host "         mot APK ky bang chung chi khac. Go app cu roi cai lai:" -ForegroundColor Yellow
    Write-Host "         adb -s $target uninstall $package" -ForegroundColor Yellow
    exit $LASTEXITCODE
}

if ($Launch) {
    Write-Host "[PRANA] Mo app..." -ForegroundColor Cyan
    # am start writes to stdout only; monkey spreads across streams, which
    # Windows PowerShell turns into a NativeCommandError.
    & $adb -s $target shell am start -n "$package/com.dlv.prana_mobile.MainActivity" | Out-Null
}

Write-Host ""
Write-Host "[PRANA] CAI THANH CONG" -ForegroundColor Green
Write-Host "[PRANA] Package: $package" -ForegroundColor Green
Write-Host "[PRANA] Thiet bi: $target ($model)" -ForegroundColor Green
