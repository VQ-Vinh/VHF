[CmdletBinding()]
param(
    [ValidateSet("staging", "production")]
    [string]$Flavor = "staging",

    [ValidateSet("auto", "debug", "release")]
    [string]$BuildMode = "auto",

    [string]$ApiUrl = "",

    [switch]$PhysicalDevice,

    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$appRoot = Split-Path -Parent $PSScriptRoot
$repoRoot = Split-Path -Parent (Split-Path -Parent $appRoot)
$configPath = Join-Path $appRoot "config\$Flavor.json"
$androidStudioJdk = "C:\Program Files\Android\Android Studio\jbr"
$resolvedMode = if ($BuildMode -eq "auto") {
    if ($Flavor -eq "production") { "release" } else { "debug" }
} else {
    $BuildMode
}

$flutterCommand = Get-Command flutter.bat -ErrorAction SilentlyContinue
if ($flutterCommand) {
    $flutter = $flutterCommand.Source
} else {
    $fallbackFlutter = Join-Path $env:USERPROFILE "develop\flutter\bin\flutter.bat"
    if (-not (Test-Path -LiteralPath $fallbackFlutter)) {
        throw "Khong tim thay Flutter SDK. Hay them Flutter vao PATH hoac cai tai $fallbackFlutter."
    }
    $flutter = $fallbackFlutter
}

foreach ($requiredPath in @($appRoot, $configPath)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Khong tim thay: $requiredPath"
    }
}

if (Test-Path -LiteralPath $androidStudioJdk) {
    $env:JAVA_HOME = $androidStudioJdk
    $env:Path = "$(Join-Path $androidStudioJdk 'bin');$env:Path"
}

if (-not $env:ANDROID_SDK_ROOT) {
    $env:ANDROID_SDK_ROOT = Join-Path $env:LOCALAPPDATA "Android\Sdk"
}

$modeArgument = "--$resolvedMode"
$flutterBuildDir = Join-Path $repoRoot "build\buildapp\flutter"
$flutterBuildDirSetting = "..\..\build\buildapp\flutter"
$expectedApk = Join-Path $flutterBuildDir "app\outputs\flutter-apk\app-$Flavor-$resolvedMode.apk"
$localApk = Join-Path $appRoot "build\app\outputs\flutter-apk\app-$Flavor-$resolvedMode.apk"
$installerDir = Join-Path $repoRoot "installers\android\$Flavor"
$installerApk = Join-Path $installerDir "prana-elex-$Flavor-$resolvedMode.apk"
$versionPath = Join-Path $repoRoot "packages\prana_core\src\prana_core\VERSION"
$appVersion = (Get-Content -LiteralPath $versionPath -Raw).Trim()

Write-Host "[PRANA] Flutter: $flutter" -ForegroundColor Cyan
Write-Host "[PRANA] Flavor: $Flavor | Mode: $resolvedMode" -ForegroundColor Cyan
Write-Host "[PRANA] Config: $configPath" -ForegroundColor Cyan
if ($PhysicalDevice -and -not $ApiUrl) {
    Write-Host "[PRANA] Physical device: su dung Cloud API trong config/$Flavor.json." -ForegroundColor Cyan
}
if ($ApiUrl) {
    $parsedApiUrl = $null
    if (
        -not [Uri]::TryCreate($ApiUrl, [UriKind]::Absolute, [ref]$parsedApiUrl) -or
        $parsedApiUrl.Scheme -notin @("http", "https")
    ) {
        throw "ApiUrl phai la dia chi HTTP/HTTPS hop le."
    }
    Write-Host "[PRANA] API override: $ApiUrl" -ForegroundColor Cyan
}

Push-Location $appRoot
$buildExitCode = 0
try {
    # Flutter SDK versions differ on whether they honor the configured
    # build-dir. Remove only the exact APK candidates so this invocation can
    # never publish an artifact left by an earlier build.
    foreach ($oldApk in @($expectedApk, $localApk, $installerApk)) {
        if (Test-Path -LiteralPath $oldApk) {
            Remove-Item -LiteralPath $oldApk -Force
        }
    }

    if ($Clean) {
        Write-Host "[PRANA] Don Android build cache..." -ForegroundColor Yellow
        if (Test-Path -LiteralPath $flutterBuildDir) {
            Remove-Item -LiteralPath $flutterBuildDir -Recurse -Force
        }
    }

    Write-Host "[PRANA] Cai dependency..." -ForegroundColor Cyan
    & $flutter pub get
    $buildExitCode = $LASTEXITCODE
    if ($buildExitCode -eq 0) {
        # Older Flutter SDKs do not accept --build-dir on `flutter build apk`.
        # Configure it for this build, then restore Flutter's default afterwards.
        & $flutter config "--build-dir=$flutterBuildDirSetting" | Out-Host
        $buildExitCode = $LASTEXITCODE
    }

    if ($buildExitCode -eq 0) {
        Write-Host "[PRANA] Build APK..." -ForegroundColor Cyan
        $buildArguments = @(
            "build", "apk",
            $modeArgument,
            "--flavor", $Flavor,
            "--build-name", $appVersion,
            "--dart-define-from-file=config/$Flavor.json"
        )
        if ($ApiUrl) {
            $buildArguments += "--dart-define=API_URL=$ApiUrl"
        }
        & $flutter @buildArguments
        $buildExitCode = $LASTEXITCODE
    }
} finally {
    & $flutter config "--build-dir=build" | Out-Host
    Pop-Location
}

if ($buildExitCode -ne 0) { exit $buildExitCode }

$sourceApk = @($expectedApk, $localApk) |
    Where-Object { Test-Path -LiteralPath $_ } |
    ForEach-Object { Get-Item -LiteralPath $_ } |
    Sort-Object LastWriteTimeUtc -Descending |
    Select-Object -First 1
if (-not $sourceApk) {
    throw "Flutter bao thanh cong nhung khong tim thay APK: $expectedApk hoac $localApk"
}

# Some Flutter SDK versions keep the Gradle APK under apps/android/build even
# when build-dir is configured. Normalize it into the repository build tree.
if ($sourceApk.FullName -ne $expectedApk) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $expectedApk) | Out-Null
    Copy-Item -LiteralPath $sourceApk.FullName -Destination $expectedApk -Force
}

$apk = Get-Item -LiteralPath $expectedApk
New-Item -ItemType Directory -Force -Path $installerDir | Out-Null
Copy-Item -LiteralPath $expectedApk -Destination $installerApk -Force
Write-Host ""
Write-Host "[PRANA] BUILD THANH CONG" -ForegroundColor Green
Write-Host "[PRANA] APK: $($apk.FullName)" -ForegroundColor Green
Write-Host "[PRANA] Installer: $installerApk" -ForegroundColor Green
Write-Host "[PRANA] Kich thuoc: $([math]::Round($apk.Length / 1MB, 2)) MB" -ForegroundColor Green
