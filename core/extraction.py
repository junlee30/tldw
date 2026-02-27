"""Frame extraction from video using ffmpeg."""

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from config import (
    CARD_WIDTH,
    CARD_HEIGHT,
    FRAME_SEARCH_WINDOW,
    FRAME_CANDIDATES,
)

logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    """Raised when frame extraction fails."""


def _check_ffmpeg() -> None:
    """Verify ffmpeg is available on PATH."""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        raise ExtractionError(
            "ffmpeg not found on PATH. Install it with: winget install ffmpeg"
        )


def _extract_single_frame(
    video_path: Path, timestamp: float, output_path: Path
) -> None:
    """Extract a single frame from video at the given timestamp."""
    cmd = [
        "ffmpeg",
        "-ss", str(timestamp),
        "-i", str(video_path),
        "-frames:v", "1",
        "-q:v", "2",
        str(output_path),
        "-y",
    ]
    result = subprocess.run(cmd, capture_output=True, check=False)
    if result.returncode != 0:
        raise ExtractionError(
            f"ffmpeg failed at timestamp {timestamp}: {result.stderr.decode()}"
        )


def _compute_sharpness(image_path: Path) -> float:
    """Compute sharpness score using Laplacian variance."""
    img = Image.open(image_path).convert("L")  # Grayscale
    arr = np.array(img, dtype=np.float64)

    # Laplacian kernel
    laplacian = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float64)

    # Manual 2D convolution (valid mode)
    h, w = arr.shape
    kh, kw = laplacian.shape
    out_h, out_w = h - kh + 1, w - kw + 1
    output = np.zeros((out_h, out_w), dtype=np.float64)

    for i in range(kh):
        for j in range(kw):
            output += arr[i:i + out_h, j:j + out_w] * laplacian[i, j]

    return float(np.var(output))


def _extract_best_frame(
    video_path: Path, timestamp: float, temp_dir: Path
) -> Path | None:
    """Extract multiple frames around timestamp and return the sharpest."""
    candidates = []
    step = (2 * FRAME_SEARCH_WINDOW) / (FRAME_CANDIDATES - 1)

    for i in range(FRAME_CANDIDATES):
        t = max(0, timestamp - FRAME_SEARCH_WINDOW + i * step)
        frame_path = temp_dir / f"candidate_{i}.jpg"
        try:
            _extract_single_frame(video_path, t, frame_path)
            if frame_path.exists():
                score = _compute_sharpness(frame_path)
                candidates.append((frame_path, score))
        except ExtractionError:
            logger.debug(f"Failed to extract frame at {t}s, skipping")
            continue

    if not candidates:
        return None

    best = max(candidates, key=lambda x: x[1])
    logger.debug(f"Best frame score: {best[1]:.1f}")
    return best[0]


def _resize_frame(path: Path, width: int, height: int) -> None:
    """Resize frame to exact dimensions using Lanczos resampling."""
    img = Image.open(path)
    img = img.resize((width, height), Image.LANCZOS)
    img.save(path)


def extract_frames(
    video_path: Path,
    timestamps: list[float],
    thumbnail_timestamp: float,
    output_dir: Path,
) -> tuple[list[Path], Path | None]:
    """Extract and optimize frames for all timestamps plus thumbnail.

    Returns:
        Tuple of (list of card frame paths, thumbnail frame path).
        Missing frames are represented as None-valued entries replaced
        by skipping them in the output list.
    """
    _check_ffmpeg()

    frames_dir = output_dir / "frames"
    frames_dir.mkdir(exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        card_frames: list[Path] = []

        # Extract card frames
        for i, ts in enumerate(timestamps):
            logger.info(f"Extracting frame {i + 1}/{len(timestamps)} at {ts}s")
            best = _extract_best_frame(video_path, ts, temp_path)
            if best is not None:
                dest = frames_dir / f"frame-{i:02d}.jpg"
                shutil.copy2(best, dest)
                _resize_frame(dest, CARD_WIDTH, CARD_HEIGHT)
                card_frames.append(dest)
            else:
                logger.warning(f"Could not extract frame at {ts}s, skipping")

            # Clean temp files for next iteration
            for f in temp_path.iterdir():
                f.unlink()

        # Extract thumbnail frame
        thumbnail_path = None
        logger.info(f"Extracting thumbnail frame at {thumbnail_timestamp}s")
        best = _extract_best_frame(video_path, thumbnail_timestamp, temp_path)
        if best is not None:
            thumbnail_path = frames_dir / "thumbnail.jpg"
            shutil.copy2(best, thumbnail_path)
            _resize_frame(thumbnail_path, CARD_WIDTH, CARD_HEIGHT)

    return card_frames, thumbnail_path
