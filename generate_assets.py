"""One-time script to generate TL;DW assets (watermark, favicon, apple-touch-icon)."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = Path(__file__).parent / "assets"
OVERLAYS_DIR = ASSETS_DIR / "overlays"
FONTS_DIR = ASSETS_DIR / "fonts"
STATIC_DIR = Path(__file__).parent / "web" / "static"


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


def _draw_icon(size):
    """Draw the TL;DW icon at the given size and return the image."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Dark rounded-square background
    radius = size // 4
    draw.rounded_rectangle(
        [(0, 0), (size - 1, size - 1)],
        radius=radius,
        fill=(24, 24, 27),  # near-black (matches site dark theme)
    )

    # "T" letter in white
    font_size = int(size * 0.55)
    try:
        font = ImageFont.truetype(str(FONTS_DIR / "Inter-Bold.ttf"), font_size)
    except OSError:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), "T", font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (size - tw) // 2 - bbox[0]
    ty = (size - th) // 2 - bbox[1]
    draw.text((tx, ty), "T", fill=(255, 255, 255), font=font)

    return img


def generate_favicon():
    """Generate a multi-size favicon.ico."""
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

    # Generate at multiple sizes for sharp rendering
    sizes = [16, 32, 48]
    images = [_draw_icon(s) for s in sizes]

    # Save to both assets and static
    for dest in [ASSETS_DIR / "favicon.ico", STATIC_DIR / "favicon.ico"]:
        images[0].save(
            dest,
            "ICO",
            sizes=[(s, s) for s in sizes],
            append_images=images[1:],
        )
    print(f"Favicon saved: {STATIC_DIR / 'favicon.ico'}")


def generate_apple_touch_icon():
    """Generate a 180x180 apple-touch-icon.png."""
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

    img = _draw_icon(180)

    output = STATIC_DIR / "apple-touch-icon.png"
    img.save(output, "PNG")
    print(f"Apple touch icon saved: {output}")


if __name__ == "__main__":
    generate_watermark()
    generate_favicon()
    generate_apple_touch_icon()
    print("Assets generated successfully!")
