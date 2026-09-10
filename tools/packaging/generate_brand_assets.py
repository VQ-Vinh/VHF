"""Render every PRANA ELEX logo asset from the brand master.

The master is `tools/packaging/brand/prana-elex-logo.png`, 1254x1254 with an
alpha channel: the mark above the "PRANA ELEX" wordmark. Assets are rendered
from it rather than resized from each other, so nothing is ever enlarged past
the detail it carries.

A vector master would be better and was tried. The SVG supplied alongside this
PNG is an incomplete trace: its mark measures 717x772 where the PNG's is
990x884, losing the outer sweep on the right entirely. Replace this file the
day a faithful vector exists, and drop the resampling here for a path renderer.

Run from the repository root:

    python tools/packaging/generate_brand_assets.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
MASTER = Path(__file__).resolve().parent / "brand" / "prana-elex-logo.png"

# The master leaves a transparent band between the mark and the wordmark. The
# mark's tail is thin enough to break into several bands above it, so the split
# sits inside the last and widest one rather than the first found.
WORDMARK_GAP = 1015

# The canvas behind iOS icons. Apple rejects alpha in app icons, so they are
# composited rather than left transparent like every other target.
CANVAS = (242, 247, 252)


def load_master() -> tuple[Image.Image, Image.Image]:
    """Return the mark and the full lockup, each trimmed to its own artwork."""
    master = Image.open(MASTER).convert("RGBA")
    lockup = master.crop(master.getchannel("A").getbbox())
    above = master.crop((0, 0, master.width, WORDMARK_GAP))
    mark = above.crop(above.getchannel("A").getbbox())
    if mark.height >= lockup.height:
        raise SystemExit("wordmark split failed; check WORDMARK_GAP against the master")
    return mark, lockup


def render(
    artwork: Image.Image,
    width: int,
    height: int,
    *,
    content_width: float | None = None,
    content_height: float | None = None,
    background: tuple[int, int, int] | None = None,
) -> Image.Image:
    """Fit the artwork on a canvas, centred, without distorting it."""
    if content_width is not None:
        scale = content_width / artwork.width
    elif content_height is not None:
        scale = content_height / artwork.height
    else:
        scale = min(width / artwork.width, height / artwork.height)

    size = (max(1, round(artwork.width * scale)), max(1, round(artwork.height * scale)))
    resized = artwork.resize(size, Image.LANCZOS)
    offset = ((width - size[0]) // 2, (height - size[1]) // 2)

    if background is None:
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        canvas.paste(resized, offset, resized)
        return canvas
    canvas = Image.new("RGB", (width, height), background)
    canvas.paste(resized, offset, resized)
    return canvas


def write(image: Image.Image, relative: str) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "PNG", optimize=True)
    print(f"  {image.size[0]:>5}x{image.size[1]:<5} {relative}")


def main() -> None:
    mark, lockup = load_master()
    print(f"master: mark {mark.size}, lockup {lockup.size}")

    print("Flutter app")
    # Canvas proportions and the share of the canvas the artwork covers are
    # carried over from the assets these replace, so no screen shifts.
    write(
        render(mark, 1024, 1024, content_height=1024 * 0.721),
        "apps/android/assets/logo_mark.png",
    )
    write(
        render(lockup, 1280, 920, content_height=920 * 0.90),
        "apps/android/assets/logo_lockup.png",
    )

    print("Android launcher and splash")
    res = "apps/android/android/app/src/main/res"
    # Adaptive icons and the Android 12 splash both guarantee only the inner
    # circle, two thirds of the canvas across. The wordmark sits at the bottom
    # of the lockup, where that circle is at its narrowest, so a lockup wider
    # than the inscribed rectangle loses its first and last letter -- 252 cost
    # "P" and "X". 208 keeps the whole lockup inside the mask.
    write(render(lockup, 432, 432, content_width=208), f"{res}/drawable/ic_launcher_foreground.png")
    write(render(lockup, 432, 432, content_width=208), f"{res}/drawable/splash_logo.png")
    for bucket, size in (
        ("mdpi", 48), ("hdpi", 72), ("xhdpi", 96), ("xxhdpi", 144), ("xxxhdpi", 192),
    ):
        write(
            render(lockup, size, size, content_width=round(size * 0.76)),
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
            render(lockup, size, size, content_width=size * 0.80, background=CANVAS),
            f"{icons}/{name}.png",
        )

    print("Web Admin")
    # The sidebar draws into 42px and the favicon into 32px, where the wordmark
    # would be a smudge, so those two keep the mark alone.
    admin = ROOT / "services/prana_admin/static/logo_mark.png"
    admin.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "apps/android/assets/logo_mark.png", admin)
    print("   copied from the app asset  services/prana_admin/static/logo_mark.png")
    write(
        render(mark, 32, 32, content_width=32 * 0.88),
        "services/prana_admin/static/favicon-32.png",
    )
    write(
        render(lockup, 180, 180, content_width=180 * 0.80, background=CANVAS),
        "services/prana_admin/static/apple-touch-icon.png",
    )


if __name__ == "__main__":
    main()
