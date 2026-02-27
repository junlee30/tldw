"""One-time script to generate TL;DW assets (watermark, favicon)."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = Path(__file__).parent / "assets"
OVERLAYS_DIR = ASSETS_DIR / "overlays"
FONTS_DIR = ASSETS_DIR / "fonts"


def generate_watermark():
    """Generate the TL;DW watermark PNG."""
    OVERLAYS_DIR.mkdir(parents=True, exist_ok=True)

    width, height = 200, 50
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Try to use Inter font, fall back to default
    try:
        font = ImageFont.truetype(str(FONTS_DIR / "Inter-Bold.ttf"), 22)
    except OSError:
        font = ImageFont.load_default()

    text = "TL;DW"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    # Pill background
    pad_x, pad_y = 16, 8
    pill_w = tw + pad_x * 2
    pill_h = th + pad_y * 2

    # Center in image
    x = (width - pill_w) // 2
    y = (height - pill_h) // 2

    draw.rounded_rectangle(
        [(x, y), (x + pill_w, y + pill_h)],
        radius=pill_h // 2,
        fill=(255, 255, 255, 140),
    )
    draw.text((x + pad_x, y + pad_y), text, fill=(10, 10, 10, 200), font=font)

    # Trim to content
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)

    output = OVERLAYS_DIR / "tldw_watermark.png"
    img.save(output, "PNG")
    print(f"Watermark saved: {output}")


def generate_favicon():
    """Generate a simple favicon."""
    size = 32
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Simple circle with "T"
    draw.ellipse([(0, 0), (size - 1, size - 1)], fill=(255, 255, 255))

    try:
        font = ImageFont.truetype(str(FONTS_DIR / "Inter-Bold.ttf"), 20)
    except OSError:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), "T", font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(
        ((size - tw) // 2, (size - th) // 2 - 2),
        "T",
        fill=(10, 10, 10),
        font=font,
    )

    output = ASSETS_DIR / "favicon.ico"
    img.save(output, "ICO", sizes=[(32, 32)])
    print(f"Favicon saved: {output}")


if __name__ == "__main__":
    generate_watermark()
    generate_favicon()
    print("Assets generated successfully!")
