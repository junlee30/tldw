"""Tests for core.composition module."""

import pytest
from pathlib import Path
from PIL import Image, ImageFont

from core.composition import (
    _wrap_text,
    _darken_image,
    compose_card,
)
from config import CARD_WIDTH, CARD_HEIGHT


def _make_test_image(path: Path, width=1280, height=720) -> Path:
    """Create a solid test image."""
    img = Image.new("RGB", (width, height), (200, 100, 50))
    img.save(path)
    return path


class TestWrapText:
    def _get_font(self):
        # Use default font for testing
        return ImageFont.load_default()

    def test_short_text(self):
        font = self._get_font()
        lines = _wrap_text("Short", font, 500)
        assert lines == ["Short"]

    def test_long_text(self):
        font = self._get_font()
        long_text = "This is a much longer piece of text that should definitely wrap across multiple lines when rendered"
        lines = _wrap_text(long_text, font, 100)
        assert len(lines) > 1

    def test_single_long_word(self):
        font = self._get_font()
        lines = _wrap_text("Supercalifragilisticexpialidocious", font, 50)
        # Should handle gracefully — at minimum return the word
        assert len(lines) >= 1


class TestDarkenImage:
    def test_pixels_are_darker(self):
        img = Image.new("RGB", (10, 10), (200, 200, 200))
        darkened = _darken_image(img, 0.5)
        orig_pixel = img.getpixel((5, 5))
        dark_pixel = darkened.getpixel((5, 5))
        assert all(d < o for d, o in zip(dark_pixel, orig_pixel))


class TestComposeCard:
    def test_dimensions(self, tmp_path):
        frame_path = _make_test_image(tmp_path / "frame.jpg")
        output_path = tmp_path / "card.webp"

        compose_card(
            frame_path=frame_path,
            segment_index=0,
            total_segments=7,
            headline="Test Headline",
            summary="This is a test summary for the card.",
            timestamp_display="1:05",
            output_path=output_path,
        )

        assert output_path.exists()
        img = Image.open(output_path)
        assert img.size == (CARD_WIDTH, CARD_HEIGHT)

    def test_format_is_webp(self, tmp_path):
        frame_path = _make_test_image(tmp_path / "frame.jpg")
        output_path = tmp_path / "card.webp"

        compose_card(
            frame_path=frame_path,
            segment_index=2,
            total_segments=5,
            headline="Format Test",
            summary="Testing WebP format output.",
            timestamp_display="2:30",
            output_path=output_path,
        )

        img = Image.open(output_path)
        assert img.format == "WEBP"
