"""Tests for core.extraction module."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from PIL import Image
import numpy as np

from core.extraction import (
    _compute_sharpness,
    _check_ffmpeg,
    ExtractionError,
)


class TestComputeSharpness:
    def test_sharp_vs_blurry(self, tmp_path):
        # Create a "sharp" image with high-frequency edges
        sharp_arr = np.zeros((100, 100, 3), dtype=np.uint8)
        for i in range(0, 100, 2):
            sharp_arr[i, :, :] = 255  # alternating black/white rows
        sharp_img = Image.fromarray(sharp_arr)
        sharp_path = tmp_path / "sharp.png"
        sharp_img.save(sharp_path)

        # Create a "blurry" image with uniform color
        blurry_arr = np.full((100, 100, 3), 128, dtype=np.uint8)
        blurry_img = Image.fromarray(blurry_arr)
        blurry_path = tmp_path / "blurry.png"
        blurry_img.save(blurry_path)

        sharp_score = _compute_sharpness(sharp_path)
        blurry_score = _compute_sharpness(blurry_path)

        assert sharp_score > blurry_score


class TestCheckFfmpeg:
    @patch("core.extraction.subprocess.run")
    def test_ffmpeg_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError()
        with pytest.raises(ExtractionError, match="ffmpeg"):
            _check_ffmpeg()

    @patch("core.extraction.subprocess.run")
    def test_ffmpeg_found(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        _check_ffmpeg()  # Should not raise


class TestExtractSingleFrame:
    @patch("core.extraction.subprocess.run")
    def test_command_args(self, mock_run, tmp_path):
        from core.extraction import _extract_single_frame

        mock_run.return_value = MagicMock(returncode=0)
        video_path = tmp_path / "video.mp4"
        output_path = tmp_path / "frame.jpg"

        # Create a dummy output file so the function doesn't fail
        output_path.write_bytes(b"fake image data")

        _extract_single_frame(video_path, 65.0, output_path)

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "ffmpeg" in cmd
        assert "-ss" in cmd
        assert "65.0" in cmd


class TestExtractBestFrame:
    @patch("core.extraction._compute_sharpness")
    @patch("core.extraction._extract_single_frame")
    def test_selects_sharpest(self, mock_extract, mock_sharpness, tmp_path):
        from core.extraction import _extract_best_frame

        # Make _extract_single_frame create dummy files
        def create_file(video_path, timestamp, output_path):
            output_path.write_bytes(b"fake image")

        mock_extract.side_effect = create_file

        # FRAME_CANDIDATES is now 2, so only 2 sharpness scores
        mock_sharpness.side_effect = [10.0, 50.0]

        result = _extract_best_frame(
            tmp_path / "video.mp4", 30.0, tmp_path
        )

        assert result is not None
        assert mock_sharpness.call_count == 2
