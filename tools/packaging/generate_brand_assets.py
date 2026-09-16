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

import io
import shutil
import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

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


# Windows desktop brand colours, from apps/android/lib/core/theme.dart. The
# desktop app reads its own tokens from prana_windows/ui/theme.py; a test pins
# that these agree, so the installer and the running app cannot drift apart.
NAVY = (13, 43, 79)          # #0D2B4F
BRAND_BLUE = (18, 63, 126)   # #123F7E
BLUE_BRIGHT = (78, 143, 213) # #4E8FD5
MUTED_ON_NAVY = (158, 188, 194)  # #9EBCC2

DESKTOP_RESOURCES = "apps/windows/src/prana_windows/ui/resources"
DESKTOP_INSTALLER = "apps/windows/packaging/installer/assets"
FONT_DIR = ROOT / "apps/android/assets/fonts"


def tinted(artwork: Image.Image, colour: tuple[int, int, int]) -> Image.Image:
    """Recolour single-ink artwork, keeping its alpha -- PIL's BlendMode.srcIn."""
    solid = Image.new("RGBA", artwork.size, (*colour, 255))
    solid.putalpha(artwork.getchannel("A"))
    return solid


def app_tile(mark: Image.Image, size: int) -> Image.Image:
    """The desktop icon: a navy rounded square carrying the white mark.

    A filled tile rather than a bare mark, because the same artwork has to read
    on a light and a dark taskbar. Each size is rendered from the master rather
    than scaled down from a larger frame -- the 16px frame is where a resample
    shows.
    """
    scale = 4  # supersample the rounded corners, then downsample once
    big = size * scale
    tile = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    ImageDraw.Draw(tile).rounded_rectangle(
        (0, 0, big - 1, big - 1), radius=round(big * 0.2), fill=(*NAVY, 255)
    )
    glyph = render(tinted(mark, (255, 255, 255)), big, big, content_width=big * 0.66)
    tile.alpha_composite(glyph)
    return tile.resize((size, size), Image.LANCZOS)


def write_ico(frames: list[Image.Image], relative: str) -> None:
    """A Windows .ico with PNG-compressed frames, one per size.

    Pillow's own ICO writer downscales a single source image; this keeps every
    frame as rendered.
    """
    blobs = []
    for frame in frames:
        buffer = io.BytesIO()
        frame.save(buffer, "PNG", optimize=True)
        blobs.append((frame.size[0], buffer.getvalue()))
    offset = 6 + 16 * len(blobs)
    entries, payload = [], []
    for size, png in blobs:
        dimension = 0 if size >= 256 else size
        entries.append(struct.pack("<BBBBHHII", dimension, dimension, 0, 0, 1, 32, len(png), offset))
        payload.append(png)
        offset += len(png)
    data = struct.pack("<HHH", 0, 1, len(blobs)) + b"".join(entries) + b"".join(payload)
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    print(f"  {len(blobs)} frames  {relative}")


def wizard_banner(lockup: Image.Image) -> Image.Image:
    """Inno Setup's side panel: 430x824, navy, white lockup, brand-face tagline."""
    width, height = 430, 824
    banner = Image.new("RGB", (width, height), NAVY)
    draw = ImageDraw.Draw(banner)
    # A quiet sweep in the brand blue, standing in for the old teal wave. It
    # starts below the tagline: crossing the mark's tail read as a mistake.
    draw.pieslice((-width, height - 150, width * 2, height + 690), 180, 360, fill=BRAND_BLUE)
    art = render(tinted(lockup, (255, 255, 255)), width, width, content_width=width * 0.62)
    banner.paste(art, (0, 150), art)
    rule_y = 150 + width - 30
    draw.rectangle((width * 0.3, rule_y, width * 0.7, rule_y + 2), fill=BLUE_BRIGHT)
    face = ImageFont.truetype(str(FONT_DIR / "Archivo-Bold.ttf"), 20)
    for index, line in enumerate(("MARINE VHF", "TRANSCRIPTION & TRANSLATION")):
        box = draw.textbbox((0, 0), line, font=face)
        x = (width - (box[2] - box[0])) // 2
        draw.text((x, rule_y + 26 + index * 32), line, font=face, fill=MUTED_ON_NAVY)
    return banner


def windows_desktop(mark: Image.Image, lockup: Image.Image) -> None:
    print("Windows desktop")
    # In-app mark, recoloured at runtime from the theme the way PranaLogo.mark
    # takes a colour on the phone.
    write(render(mark, 128, 128, content_height=128 * 0.721), f"{DESKTOP_RESOURCES}/logo_mark.png")

    # One icon for the exe, installer, window, taskbar and tray. The UI copy is
    # the same bytes, so the running app never needs the installer tree.
    frames = [app_tile(mark, size) for size in (16, 32, 48, 64, 256)]
    write_ico(frames, f"{DESKTOP_INSTALLER}/prana-elex.ico")
    shutil.copyfile(ROOT / DESKTOP_INSTALLER / "prana-elex.ico", ROOT / DESKTOP_RESOURCES / "prana-elex.ico")
    print(f"   copied  {DESKTOP_RESOURCES}/prana-elex.ico")

    write(wizard_banner(lockup), f"{DESKTOP_INSTALLER}/wizard-banner.png")
    write(app_tile(mark, 116).convert("RGBA"), f"{DESKTOP_INSTALLER}/wizard-logo.png")

    # The brand faces travel with their OFL licences, byte for byte.
    fonts = ROOT / DESKTOP_RESOURCES / "fonts"
    fonts.mkdir(parents=True, exist_ok=True)
    for source in sorted(FONT_DIR.iterdir()):
        if source.suffix in {".ttf", ".txt"}:
            shutil.copyfile(source, fonts / source.name)
    print(f"   copied fonts  {DESKTOP_RESOURCES}/fonts")


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

    windows_desktop(mark, lockup)


if __name__ == "__main__":
    main()
