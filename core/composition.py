"""Card composition: combine frames with text overlays."""

import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from config import (
    CARD_WIDTH,
    CARD_HEIGHT,
    FONT_BOLD,
    FONT_REGULAR,
    WATERMARK_PATH,
    HEADLINE_FONT_SIZE,
    SUMMARY_FONT_SIZE,
    BADGE_FONT_SIZE,
    COUNTER_FONT_SIZE,
    DARKEN_FACTOR,
    GRADIENT_HEIGHT_RATIO,
)

logger = logging.getLogger(__name__)


def _load_fonts() -> tuple[ImageFont.FreeTypeFont, ...]:
    """Load Inter fonts. Falls back to default if not found."""
    try:
        headline_font = ImageFont.truetype(str(FONT_BOLD), HEADLINE_FONT_SIZE)
        summary_font = ImageFont.truetype(str(FONT_REGULAR), SUMMARY_FONT_SIZE)
        badge_font = ImageFont.truetype(str(FONT_BOLD), BADGE_FONT_SIZE)
        counter_font = ImageFont.truetype(str(FONT_BOLD), COUNTER_FONT_SIZE)
    except OSError:
        logger.warning("Inter fonts not found, using default font")
        headline_font = ImageFont.load_default()
        summary_font = ImageFont.load_default()
        badge_font = ImageFont.load_default()
        counter_font = ImageFont.load_default()
    return headline_font, summary_font, badge_font, counter_font


def _darken_image(image: Image.Image, factor: float = DARKEN_FACTOR) -> Image.Image:
    """Darken an image by the given factor."""
    enhancer = ImageEnhance.Brightness(image)
    return enhancer.enhance(factor)


def _draw_gradient_overlay(image: Image.Image) -> Image.Image:
    """Draw a gradient overlay on the bottom portion of the image."""
    img = image.copy()
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    gradient_start = int(img.height * (1 - GRADIENT_HEIGHT_RATIO))
    for y in range(gradient_start, img.height):
        progress = (y - gradient_start) / (img.height - gradient_start)
        alpha = int(200 * progress)
        draw.line([(0, y), (img.width, y)], fill=(0, 0, 0, alpha))

    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay)
    return img.convert("RGB")


def _wrap_text(text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    """Word-wrap text to fit within max_width pixels."""
    words = text.split()
    if not words:
        return [""]

    lines = []
    current_line = words[0]

    # Use a temporary image for text measurement
    tmp_img = Image.new("RGB", (1, 1))
    tmp_draw = ImageDraw.Draw(tmp_img)

    for word in words[1:]:
        test_line = f"{current_line} {word}"
        bbox = tmp_draw.textbbox((0, 0), test_line, font=font)
        text_width = bbox[2] - bbox[0]

        if text_width <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word

    lines.append(current_line)
    return lines


def _draw_timestamp_badge(
    draw: ImageDraw.Draw,
    timestamp_display: str,
    font: ImageFont.FreeTypeFont,
    image_width: int,
    image_height: int,
) -> None:
    """Draw a rounded timestamp pill badge."""
    bbox = draw.textbbox((0, 0), timestamp_display, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    pad_x, pad_y = 14, 8
    badge_w = text_w + pad_x * 2
    badge_h = text_h + pad_y * 2
    x = image_width - badge_w - 24
    y = 24

    # Semi-transparent background
    badge_img = Image.new("RGBA", (badge_w, badge_h), (0, 0, 0, 160))
    draw_badge = ImageDraw.Draw(badge_img)
    draw_badge.rounded_rectangle(
        [(0, 0), (badge_w - 1, badge_h - 1)],
        radius=badge_h // 2,
        fill=(0, 0, 0, 160),
    )
    draw_badge.text(
        (pad_x, pad_y), timestamp_display, fill=(255, 255, 255), font=font
    )

    # We need to composite this onto the main image
    # Store for later compositing
    return badge_img, (x, y)


def _draw_segment_counter(
    draw: ImageDraw.Draw,
    index: int,
    total: int,
    font: ImageFont.FreeTypeFont,
) -> None:
    """Draw segment counter (e.g., '3/7') in top-left corner."""
    text = f"{index + 1}/{total}"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    pad_x, pad_y = 12, 6
    badge_w = text_w + pad_x * 2
    badge_h = text_h + pad_y * 2
    x, y = 24, 24

    draw.rounded_rectangle(
        [(x, y), (x + badge_w, y + badge_h)],
        radius=badge_h // 2,
        fill=(255, 255, 255, 40),
    )
    draw.text(
        (x + pad_x, y + pad_y),
        text,
        fill=(255, 255, 255, 200),
        font=font,
    )


def compose_card(
    frame_path: Path,
    segment_index: int,
    total_segments: int,
    headline: str,
    summary: str,
    timestamp_display: str,
    output_path: Path,
) -> None:
    """Compose a single card image from a frame and text."""
    headline_font, summary_font, badge_font, counter_font = _load_fonts()

    # Load and prepare frame
    img = Image.open(frame_path).convert("RGB")
    img = img.resize((CARD_WIDTH, CARD_HEIGHT), Image.LANCZOS)
    img = _darken_image(img)
    img = _draw_gradient_overlay(img)

    # Convert to RGBA for compositing
    img = img.convert("RGBA")

    # Draw timestamp badge
    badge_img, badge_pos = _draw_timestamp_badge(
        ImageDraw.Draw(img), timestamp_display, badge_font, CARD_WIDTH, CARD_HEIGHT
    )
    img.paste(badge_img, badge_pos, badge_img)

    draw = ImageDraw.Draw(img)

    # Segment counter
    _draw_segment_counter(draw, segment_index, total_segments, counter_font)

    # Text area dimensions
    text_margin = 48
    text_max_width = CARD_WIDTH - text_margin * 2

    # Headline — positioned from bottom up
    headline_lines = _wrap_text(headline, headline_font, text_max_width)
    summary_lines = _wrap_text(summary, summary_font, text_max_width)

    # Calculate total text height
    line_spacing_headline = 6
    line_spacing_summary = 4

    headline_total_h = 0
    for line in headline_lines:
        bbox = draw.textbbox((0, 0), line, font=headline_font)
        headline_total_h += (bbox[3] - bbox[1]) + line_spacing_headline

    summary_total_h = 0
    for line in summary_lines:
        bbox = draw.textbbox((0, 0), line, font=summary_font)
        summary_total_h += (bbox[3] - bbox[1]) + line_spacing_summary

    gap_between = 16
    total_text_h = headline_total_h + gap_between + summary_total_h
    text_bottom_margin = 48

    # Start Y for headline
    y = CARD_HEIGHT - text_bottom_margin - total_text_h

    # Draw headline
    for line in headline_lines:
        draw.text((text_margin, y), line, fill=(255, 255, 255), font=headline_font)
        bbox = draw.textbbox((0, 0), line, font=headline_font)
        y += (bbox[3] - bbox[1]) + line_spacing_headline

    y += gap_between - line_spacing_headline

    # Draw summary
    for line in summary_lines:
        draw.text(
            (text_margin, y),
            line,
            fill=(255, 255, 255, 200),
            font=summary_font,
        )
        bbox = draw.textbbox((0, 0), line, font=summary_font)
        y += (bbox[3] - bbox[1]) + line_spacing_summary

    # Watermark
    _apply_watermark(img)

    # Save as WebP
    img = img.convert("RGB")
    img.save(output_path, "WEBP", quality=90)
    logger.info(f"Card saved: {output_path}")


def _apply_watermark(image: Image.Image) -> None:
    """Apply TL;DW watermark to bottom-right corner."""
    if not WATERMARK_PATH.exists():
        return

    try:
        watermark = Image.open(WATERMARK_PATH).convert("RGBA")
        # Scale watermark to ~10% of image width
        scale = (image.width * 0.1) / watermark.width
        new_size = (int(watermark.width * scale), int(watermark.height * scale))
        watermark = watermark.resize(new_size, Image.LANCZOS)

        # Position bottom-right with margin
        margin = 16
        x = image.width - watermark.width - margin
        y = image.height - watermark.height - margin

        image.paste(watermark, (x, y), watermark)
    except Exception as e:
        logger.debug(f"Could not apply watermark: {e}")


def compose_all_cards(
    frames: list[Path],
    segments: list,
    output_dir: Path,
) -> list[Path]:
    """Compose all card images."""
    cards_dir = output_dir / "cards"
    cards_dir.mkdir(exist_ok=True)

    card_paths = []
    total = len(frames)

    for i, (frame, segment) in enumerate(zip(frames, segments)):
        output_path = cards_dir / f"card-{i:02d}.webp"
        compose_card(
            frame_path=frame,
            segment_index=i,
            total_segments=total,
            headline=segment.headline,
            summary=segment.summary,
            timestamp_display=segment.timestamp_display,
            output_path=output_path,
        )
        card_paths.append(output_path)

    logger.info(f"Composed {len(card_paths)} cards")
    return card_paths
