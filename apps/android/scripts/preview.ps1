[CmdletBinding()]
param(
    [ValidateSet('auto', 'chrome', 'edge', 'web-server')][string]$Browser = 'auto',
    [switch]$OpenBrowserWhenReady,
    [switch]$NoOpenBrowser
)
$ErrorActionPreference = 'Stop'
if ($OpenBrowserWhenReady) {
    for ($attempt = 0; $attempt -lt 120; $attempt++) {
        try {
            $null = Invoke-WebRequest 'http://127.0.0.1:8876' -UseBasicParsing -TimeoutSec 1
            Start-Process 'http://127.0.0.1:8876'
            exit 0
        } catch { Start-Sleep -Seconds 1 }
    }
    exit 1
}
$appRoot = Split-Path -Parent $PSScriptRoot
$listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 8876)
try { $listener.Start() }
catch { throw 'Port 8876 is busy. Stop the existing preview/server before retrying.' }
finally { $listener.Stop() }

$command = Get-Command flutter.bat -ErrorAction SilentlyContinue
$flutter = if ($command) { $command.Source } else {
    Join-Path $env:USERPROFILE 'develop\flutter\bin\flutter.bat'
}
if (-not (Test-Path -LiteralPath $flutter)) { throw 'Flutter SDK not found. Add flutter.bat to PATH.' }
if ($Browser -eq 'auto') {
    $chromePaths = @(
        $env:CHROME_EXECUTABLE,
        (Join-Path $env:LOCALAPPDATA 'Google\Chrome\Application\chrome.exe'),
        (Join-Path $env:ProgramFiles 'Google\Chrome\Application\chrome.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Google\Chrome\Application\chrome.exe')
    )
    $chromeFound = $chromePaths | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
    if ($chromeFound) { $env:CHROME_EXECUTABLE = $chromeFound; $Browser = 'chrome' }
    else { $Browser = 'web-server'; Write-Host '[PRANA] Chrome not found; opening the default browser with web-server.' }
}
Write-Host '[PRANA] UI Preview: http://127.0.0.1:8876 — simulated data, no backend.'
Write-Host '[PRANA] Keep this terminal open. r: hot reload, R: hot restart, q: quit.'
Push-Location -LiteralPath $appRoot
try {
    if ($Browser -eq 'web-server' -and -not $NoOpenBrowser) {
        Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @(
            '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $PSCommandPath + '"'), '-OpenBrowserWhenReady'
        ) | Out-Null
    }
    & $flutter run -d $Browser --target lib/main_preview.dart --web-hostname 127.0.0.1 --web-port 8876
    $previewExit = $LASTEXITCODE
} finally { Pop-Location }
exit $previewExit
