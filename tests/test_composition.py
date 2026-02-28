"""Tests for core.composition module."""

import pytest
from pathlib import Path
from PIL import Image

from core.composition import compose_card
from config import CARD_WIDTH, CARD_HEIGHT


def _make_test_image(path: Path, width=1280, height=720) -> Path:
    """Create a solid test image."""
    img = Image.new("RGB", (width, height), (200, 100, 50))
    img.save(path)
    return path


class TestComposeCard:
    def test_dimensions(self, tmp_path):
        frame_path = _make_test_image(tmp_path / "frame.jpg")
        output_path = tmp_path / "card.webp"

        compose_card(frame_path=frame_path, output_path=output_path)

        assert output_path.exists()
        img = Image.open(output_path)
        assert img.size == (CARD_WIDTH, CARD_HEIGHT)

    def test_format_is_webp(self, tmp_path):
        frame_path = _make_test_image(tmp_path / "frame.jpg")
        output_path = tmp_path / "card.webp"

        compose_card(frame_path=frame_path, output_path=output_path)

        img = Image.open(output_path)
        assert img.format == "WEBP"

    def test_preserves_raw_frame(self, tmp_path):
        """Card should be a clean resize — no darkening or text overlay."""
        frame_path = _make_test_image(tmp_path / "frame.jpg", 640, 360)
        output_path = tmp_path / "card.webp"

        compose_card(frame_path=frame_path, output_path=output_path)

        img = Image.open(output_path)
        # Check center pixel is still roughly the original color (200, 100, 50)
        # WebP compression may shift values slightly
        pixel = img.getpixel((CARD_WIDTH // 2, CARD_HEIGHT // 2))
        assert pixel[0] > 150  # Red channel should stay bright (no darkening)
