"""Render every PRANA ELEX logo asset from the vector master.

The master is `tools/packaging/brand/prana-elex-logo.svg`: one even-odd path in
a 1254x1254 viewBox, holding the mark above the "PRANA ELEX" wordmark. Assets
are regenerated from it rather than resized from each other, so nothing is ever
enlarged past the detail it actually carries.

The mark alone is what launchers and splash screens get. The wordmark is
illegible below roughly 128 px, so a lockup shrunk into a 48 px launcher icon
reads as a smudge -- which is what the icons looked like before this script.

Run from the repository root:

    python tools/packaging/generate_brand_assets.py
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
MASTER = Path(__file__).resolve().parent / "brand" / "prana-elex-logo.svg"

# Anti-aliasing comes from rendering this many times over and downsampling; the
# path is polygonal, so nothing else smooths the curves.
SUPERSAMPLE = 4

# The canvas behind iOS icons. Apple rejects alpha in app icons, so they are
# composited rather than left transparent like every other target.
CANVAS = (242, 247, 252)

Polygon = list[tuple[float, float]]


def load_master() -> tuple[list[Polygon], list[Polygon]]:
    """Return (mark subpaths, full lockup subpaths) from the vector master."""
    svg = MASTER.read_text(encoding="utf-8")
    data = re.search(r'\sd="([^"]+)"', svg).group(1)
    if "C" in data or "Q" in data or "A" in data:
        raise SystemExit("master gained curve commands; this renderer only walks lines")

    subpaths: list[Polygon] = []
    current: list[float] = []
    for command, number in re.findall(r"([MLZ])|(-?\d+(?:\.\d+)?)", data):
        if command:
            if command in "MZ" and current:
                subpaths.append(current)
                current = []
        else:
            current.append(float(number))
    if current:
        subpaths.append(current)

    polygons = [
        [(flat[i], flat[i + 1]) for i in range(0, len(flat) - 1, 2)]
        for flat in subpaths
    ]
    # The wordmark sits below the mark in the viewBox; split on that gap rather
    # than on subpath indexes, so re-exporting the master cannot silently
    # reorder them.
    wordmark_top = 1000.0
    mark = [p for p in polygons if min(y for _, y in p) < wordmark_top]
    if not mark or len(mark) == len(polygons):
        raise SystemExit("could not separate the mark from the wordmark")
    return mark, polygons


def render(
    polygons: list[Polygon],
    width: int,
    height: int,
    *,
    content_width: float | None = None,
    content_height: float | None = None,
    colour: tuple[int, int, int] = (0, 59, 143),
    background: tuple[int, int, int] | None = None,
) -> Image.Image:
    """Draw the polygons centred on a transparent or filled canvas."""
    xs = [x for polygon in polygons for x, _ in polygon]
    ys = [y for polygon in polygons for _, y in polygon]
    span_x, span_y = max(xs) - min(xs), max(ys) - min(ys)

    if content_width is not None:
        scale = content_width / span_x
    elif content_height is not None:
        scale = content_height / span_y
    else:
        scale = min(width / span_x, height / span_y)

    big_w, big_h = width * SUPERSAMPLE, height * SUPERSAMPLE
    scale *= SUPERSAMPLE
    offset_x = (big_w - span_x * scale) / 2 - min(xs) * scale
    offset_y = (big_h - span_y * scale) / 2 - min(ys) * scale

    # even-odd fill: XOR each subpath so the holes in the mark stay open.
    mask = Image.new("1", (big_w, big_h), 0)
    for polygon in polygons:
        layer = Image.new("1", (big_w, big_h), 0)
        ImageDraw.Draw(layer).polygon(
            [(x * scale + offset_x, y * scale + offset_y) for x, y in polygon],
            fill=1,
        )
        mask = ImageChops.logical_xor(mask, layer)

    alpha = mask.convert("L").resize((width, height), Image.LANCZOS)
    if background is None:
        image = Image.new("RGBA", (width, height), colour + (0,))
        image.putalpha(alpha)
        return image
    image = Image.new("RGB", (width, height), background)
    image.paste(Image.new("RGB", (width, height), colour), mask=alpha)
    return image


def write(image: Image.Image, relative: str) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "PNG", optimize=True)
    print(f"  {image.size[0]:>5}x{image.size[1]:<5} {relative}")


def main() -> None:
    mark, lockup = load_master()

    print("Flutter app")
    # Canvas proportions and the share of it the artwork covers are kept from
    # the assets these replace, so no screen shifts -- only the sharpness does.
    app_mark = render(mark, 1024, 1024, content_height=1024 * 0.721)
    write(app_mark, "apps/android/assets/logo_mark.png")
    write(
        render(lockup, 1280, 920, content_height=920 * 0.90),
        "apps/android/assets/logo_lockup.png",
    )

    print("Android launcher and splash")
    res = "apps/android/android/app/src/main/res"
    # 252 of 432 keeps the mark inside the adaptive icon's safe zone.
    write(render(mark, 432, 432, content_width=252), f"{res}/drawable/ic_launcher_foreground.png")
    write(render(mark, 432, 432, content_width=252), f"{res}/drawable/splash_logo.png")
    for bucket, size in (
        ("mdpi", 48), ("hdpi", 72), ("xhdpi", 96), ("xxhdpi", 144), ("xxxhdpi", 192),
    ):
        write(
            render(mark, size, size, content_width=round(size * 0.76)),
            f"{res}/mipmap-{bucket}/ic_launcher.png",
        )

    print("iOS app icon (opaque: Apple rejects alpha here)")
    icons = "apps/android/ios/Runner/Assets.xcassets/AppIcon.appiconset"
    for name, size in (
        ("Icon-App-20x20@1x", 20), ("Icon-App-20x20@2x", 40), ("Icon-App-20x20@3x", 60),
        ("Icon-App-29x29@1x", 29), ("Icon-App-29x29@2x", 58), ("Icon-App-29x29@3x", 87),
        ("Icon-App-40x40@1x", 40), ("Icon-App-40x40@2x", 80), ("Icon-App-40x40@3x", 120),
        ("Icon-App-60x60@2x", 120), ("Icon-App-60x60@3x", 180),
        ("Icon-App-76x76@1x", 76), ("Icon-App-76x76@2x", 152),
        ("Icon-App-83.5x83.5@2x", 167),
        ("Icon-App-1024x1024@1x", 1024),
    ):
        write(
            render(mark, size, size, content_width=size * 0.66, background=CANVAS),
            f"{icons}/{name}.png",
        )

    print("Web Admin")
    admin = ROOT / "services/prana_admin/static/logo_mark.png"
    admin.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "apps/android/assets/logo_mark.png", admin)
    print("   copied from the app asset  services/prana_admin/static/logo_mark.png")
    write(
        render(mark, 32, 32, content_width=32 * 0.88),
        "services/prana_admin/static/favicon-32.png",
    )
    write(
        render(mark, 180, 180, content_width=180 * 0.66, background=CANVAS),
        "services/prana_admin/static/apple-touch-icon.png",
    )


if __name__ == "__main__":
    main()
