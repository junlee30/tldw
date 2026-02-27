"""OG thumbnail generation for social media link previews."""

import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from config import (
    OG_WIDTH,
    OG_HEIGHT,
    FONT_BOLD,
    FONT_REGULAR,
    DARKEN_FACTOR,
)

logger = logging.getLogger(__name__)


def _load_og_fonts() -> tuple[ImageFont.FreeTypeFont, ...]:
    """Load fonts for OG image."""
    try:
        title_font = ImageFont.truetype(str(FONT_BOLD), 36)
        brand_font = ImageFont.truetype(str(FONT_BOLD), 28)
    except OSError:
        logger.warning("Inter fonts not found, using default font")
        title_font = ImageFont.load_default()
        brand_font = ImageFont.load_default()
    return title_font, brand_font


def _crop_to_aspect_ratio(
    image: Image.Image, target_w: int, target_h: int
) -> Image.Image:
    """Center-crop image to target aspect ratio, then resize."""
    img_w, img_h = image.size
    target_ratio = target_w / target_h
    img_ratio = img_w / img_h

    if img_ratio > target_ratio:
        # Image is wider — crop width
        new_w = int(img_h * target_ratio)
        offset = (img_w - new_w) // 2
        cropped = image.crop((offset, 0, offset + new_w, img_h))
    else:
        # Image is taller — crop height
        new_h = int(img_w / target_ratio)
        offset = (img_h - new_h) // 2
        cropped = image.crop((0, offset, img_w, offset + new_h))

    return cropped.resize((target_w, target_h), Image.LANCZOS)


def _draw_branding_overlay(
    image: Image.Image, video_title: str
) -> Image.Image:
    """Draw TL;DW branding and title overlay on the image."""
    title_font, brand_font = _load_og_fonts()

    # Darken the image
    enhancer = ImageEnhance.Brightness(image)
    img = enhancer.enhance(DARKEN_FACTOR)
    img = img.convert("RGBA")

    # Bottom gradient
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    gradient_start = int(img.height * 0.5)
    for y in range(gradient_start, img.height):
        progress = (y - gradient_start) / (img.height - gradient_start)
        alpha = int(220 * progress)
        draw_overlay.line([(0, y), (img.width, y)], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img, overlay)

    draw = ImageDraw.Draw(img)

    # TL;DW brand pill — top left
    brand_text = "TL;DW"
    bbox = draw.textbbox((0, 0), brand_text, font=brand_font)
    bw = bbox[2] - bbox[0]
    bh = bbox[3] - bbox[1]
    pad_x, pad_y = 16, 8
    pill_x, pill_y = 32, 32
    draw.rounded_rectangle(
        [(pill_x, pill_y), (pill_x + bw + pad_x * 2, pill_y + bh + pad_y * 2)],
        radius=(bh + pad_y * 2) // 2,
        fill=(255, 255, 255, 230),
    )
    draw.text(
        (pill_x + pad_x, pill_y + pad_y),
        brand_text,
        fill=(10, 10, 10),
        font=brand_font,
    )

    # Title at bottom
    margin = 40
    max_title_width = img.width - margin * 2

    # Word wrap title
    words = video_title.split()
    lines = []
    current_line = words[0] if words else ""
    for word in words[1:]:
        test = f"{current_line} {word}"
        tbbox = draw.textbbox((0, 0), test, font=title_font)
        if (tbbox[2] - tbbox[0]) <= max_title_width:
            current_line = test
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)

    # Limit to 3 lines
    if len(lines) > 3:
        lines = lines[:3]
        lines[-1] = lines[-1][:50].rstrip() + "..."

    # Draw title lines from bottom up
    line_height = 44
    total_h = len(lines) * line_height
    start_y = img.height - 40 - total_h

    for i, line in enumerate(lines):
        draw.text(
            (margin, start_y + i * line_height),
            line,
            fill=(255, 255, 255),
            font=title_font,
        )

    return img.convert("RGB")


def generate_og_image(
    frame_path: Path, video_title: str, output_path: Path
) -> None:
    """Generate OG image (1200x630) for social media link previews."""
    img = Image.open(frame_path).convert("RGB")
    img = _crop_to_aspect_ratio(img, OG_WIDTH, OG_HEIGHT)
    img = _draw_branding_overlay(img, video_title)
    img.save(output_path, "PNG")
    logger.info(f"OG image saved: {output_path}")
