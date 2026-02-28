"""Card composition: resize frames and save as WebP."""

import logging
from pathlib import Path

from PIL import Image

from config import CARD_WIDTH, CARD_HEIGHT

logger = logging.getLogger(__name__)


def compose_card(frame_path: Path, output_path: Path) -> None:
    """Compose a single card image from a frame (resize + WebP conversion)."""
    img = Image.open(frame_path).convert("RGB")
    img = img.resize((CARD_WIDTH, CARD_HEIGHT), Image.LANCZOS)
    img.save(output_path, "WEBP", quality=90)
    logger.info(f"Card saved: {output_path}")


def compose_all_cards(
    frames: list[Path],
    output_dir: Path,
) -> list[Path]:
    """Compose all card images."""
    cards_dir = output_dir / "cards"
    cards_dir.mkdir(exist_ok=True)

    card_paths = []

    for i, frame in enumerate(frames):
        output_path = cards_dir / f"card-{i:02d}.webp"
        compose_card(frame_path=frame, output_path=output_path)
        card_paths.append(output_path)

    logger.info(f"Composed {len(card_paths)} cards")
    return card_paths
