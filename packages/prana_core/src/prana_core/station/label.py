from __future__ import annotations

from html import escape
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont


def grouped(value: str) -> str:
    return " ".join(value[index:index + 4] for index in range(0, len(value), 4))


def qr_payload(setup_id: str, activation_code: str) -> str:
    return f"prana-elex:///activate?v=1&id={setup_id}&code={activation_code}"


def _font(size: int):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


def write_label(output_dir: Path, setup_id: str, activation_code: str) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = qr_payload(setup_id, activation_code)
    matrix = qrcode.QRCode(version=None, box_size=1, border=4)
    matrix.add_data(payload)
    matrix.make(fit=True)
    modules = matrix.get_matrix()

    svg_path = output_dir / f"prana-station-{setup_id}.svg"
    module_size = 8
    qr_size = len(modules) * module_size
    svg_width = qr_size + 520
    svg_height = max(qr_size, 420)
    rectangles = []
    for row, values in enumerate(modules):
        for column, enabled in enumerate(values):
            if enabled:
                rectangles.append(
                    f'<rect x="{column * module_size}" y="{row * module_size}" '
                    f'width="{module_size}" height="{module_size}"/>'
                )
    text_x = qr_size + 36
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{svg_height}" '
        f'viewBox="0 0 {svg_width} {svg_height}">'
        '<rect width="100%" height="100%" fill="white"/>'
        f'<g fill="black">{"".join(rectangles)}</g>'
        f'<g fill="#062b29" font-family="Arial, sans-serif" x="{text_x}">'
        f'<text x="{text_x}" y="85" font-size="42" font-weight="700">PRANA ELEX</text>'
        f'<text x="{text_x}" y="135" font-size="24">Station Setup</text>'
        f'<text x="{text_x}" y="215" font-size="20">SETUP ID</text>'
        f'<text x="{text_x}" y="252" font-size="30" font-weight="700">{escape(setup_id)}</text>'
        f'<text x="{text_x}" y="320" font-size="20">ACTIVATION CODE</text>'
        f'<text x="{text_x}" y="358" font-size="27" font-weight="700">{escape(grouped(activation_code))}</text>'
        f'<text x="{text_x}" y="405" font-size="17">Scan only after signing in to PRANA ELEX.</text>'
        '</g></svg>'
    )
    svg_path.write_text(svg, encoding="utf-8")

    qr_image = qrcode.make(payload).get_image().convert("RGB")
    qr_image = qr_image.resize((560, 560), Image.Resampling.NEAREST)
    png_path = output_dir / f"prana-station-{setup_id}.png"
    canvas = Image.new("RGB", (1200, 700), "white")
    canvas.paste(qr_image, (50, 70))
    draw = ImageDraw.Draw(canvas)
    font = _font(34)
    small = _font(24)
    draw.text((650, 110), "PRANA ELEX", fill="#062b29", font=font)
    draw.text((650, 175), "Station Setup", fill="#40605e", font=small)
    draw.text((650, 275), "SETUP ID", fill="#40605e", font=small)
    draw.text((650, 315), setup_id, fill="#062b29", font=font)
    draw.text((650, 410), "ACTIVATION CODE", fill="#40605e", font=small)
    draw.text((650, 450), grouped(activation_code), fill="#062b29", font=font)
    draw.text((650, 545), "Scan after signing in to PRANA ELEX.", fill="#40605e", font=small)
    canvas.save(png_path)

    try:
        output_dir.chmod(0o700)
        svg_path.chmod(0o600)
        png_path.chmod(0o600)
    except OSError:
        pass
    return png_path, svg_path
