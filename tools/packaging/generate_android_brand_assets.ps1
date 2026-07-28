[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$sourcePath = Join-Path $root "apps\android\assets\logo_lockup.png"
$resPath = Join-Path $root "apps\android\android\app\src\main\res"

if (-not (Test-Path -LiteralPath $sourcePath)) {
    throw "Logo source not found: $sourcePath"
}

function New-BrandBitmap {
    param(
        [int]$Size,
        [int]$ContentWidth,
        [string]$OutputPath,
        [switch]$White
    )

    $source = [System.Drawing.Bitmap]::FromFile($sourcePath)
    try {
        $target = New-Object System.Drawing.Bitmap(
            $Size,
            $Size,
            [System.Drawing.Imaging.PixelFormat]::Format32bppArgb
        )
        try {
            $target.SetResolution(96, 96)
            $graphics = [System.Drawing.Graphics]::FromImage($target)
            try {
                $graphics.Clear([System.Drawing.Color]::Transparent)
                $graphics.CompositingMode =
                    [System.Drawing.Drawing2D.CompositingMode]::SourceOver
                $graphics.CompositingQuality =
                    [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
                $graphics.InterpolationMode =
                    [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
                $graphics.PixelOffsetMode =
                    [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
                $graphics.SmoothingMode =
                    [System.Drawing.Drawing2D.SmoothingMode]::HighQuality

                $contentHeight = [int][Math]::Round(
                    $ContentWidth * $source.Height / $source.Width
                )
                $left = [int](($Size - $ContentWidth) / 2)
                $top = [int](($Size - $contentHeight) / 2)
                $destination = New-Object System.Drawing.Rectangle(
                    $left,
                    $top,
                    $ContentWidth,
                    $contentHeight
                )

                if ($White) {
                    $attributes = New-Object System.Drawing.Imaging.ImageAttributes
                    try {
                        $matrixValues = [single[][]]@(
                            [single[]]@(0, 0, 0, 0, 0),
                            [single[]]@(0, 0, 0, 0, 0),
                            [single[]]@(0, 0, 0, 0, 0),
                            [single[]]@(0, 0, 0, 1, 0),
                            [single[]]@(1, 1, 1, 0, 1)
                        )
                        $matrix =
                            [System.Drawing.Imaging.ColorMatrix]::new($matrixValues)
                        $attributes.SetColorMatrix($matrix)
                        $graphics.DrawImage(
                            $source,
                            $destination,
                            0,
                            0,
                            $source.Width,
                            $source.Height,
                            [System.Drawing.GraphicsUnit]::Pixel,
                            $attributes
                        )
                    } finally {
                        $attributes.Dispose()
                    }
                } else {
                    $graphics.DrawImage($source, $destination)
                }
            } finally {
                $graphics.Dispose()
            }

            $directory = Split-Path -Parent $OutputPath
            New-Item -ItemType Directory -Force -Path $directory | Out-Null
            $target.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png)
        } finally {
            $target.Dispose()
        }
    } finally {
        $source.Dispose()
    }
}

# Android adaptive icons mask everything outside their central safe zone.
# Keep the complete lockup, including the wordmark, inside that zone.
New-BrandBitmap `
    -Size 432 `
    -ContentWidth 252 `
    -OutputPath (Join-Path $resPath "drawable\ic_launcher_foreground.png")

# Android 12 also masks the splash icon, so use the same conservative safe zone.
New-BrandBitmap `
    -Size 432 `
    -ContentWidth 252 `
    -OutputPath (Join-Path $resPath "drawable\splash_logo.png")

$legacySizes = @{
    "mipmap-mdpi" = 48
    "mipmap-hdpi" = 72
    "mipmap-xhdpi" = 96
    "mipmap-xxhdpi" = 144
    "mipmap-xxxhdpi" = 192
}

foreach ($entry in $legacySizes.GetEnumerator()) {
    New-BrandBitmap `
        -Size $entry.Value `
        -ContentWidth ([int][Math]::Round($entry.Value * 0.76)) `
        -OutputPath (Join-Path $resPath "$($entry.Key)\ic_launcher.png")
}

Write-Host "[OK] Android launcher and splash brand assets generated."
