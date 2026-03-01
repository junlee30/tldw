"""Tests for core.ingestion module."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from core.ingestion import (
    extract_video_id,
    extract_audio,
    fetch_metadata,
    validate_video,
    ingest,
    IngestionError,
    VideoMetadata,
)


class TestExtractVideoId:
    def test_standard_url(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_short_url(self):
        url = "https://youtu.be/dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_shorts_url(self):
        url = "https://www.youtube.com/shorts/dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_with_extra_params(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120&list=PLtest"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_embed_url(self):
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_invalid_url(self):
        with pytest.raises(ValueError):
            extract_video_id("https://example.com/video")

    def test_empty_string(self):
        with pytest.raises(ValueError):
            extract_video_id("")

    def test_no_video_id(self):
        with pytest.raises(ValueError):
            extract_video_id("https://www.youtube.com/watch")


class TestValidateVideo:
    def test_valid_video(self):
        metadata = VideoMetadata(
            video_id="test123",
            title="Test Video",
            channel="Test Channel",
            duration=300,
            upload_date="20250115",
            description="A test video",
            thumbnail_url="https://example.com/thumb.jpg",
        )
        validate_video(metadata)  # Should not raise

    def test_too_long(self):
        metadata = VideoMetadata(
            video_id="test123",
            title="Test Video",
            channel="Test Channel",
            duration=7201,
            upload_date="20250115",
            description="A long video",
            thumbnail_url="https://example.com/thumb.jpg",
        )
        with pytest.raises(IngestionError, match="too long"):
            validate_video(metadata)

    def test_zero_duration(self):
        metadata = VideoMetadata(
            video_id="test123",
            title="Test Video",
            channel="Test Channel",
            duration=0,
            upload_date="20250115",
            description="A live stream",
            thumbnail_url="https://example.com/thumb.jpg",
        )
        with pytest.raises(IngestionError, match="too short"):
            validate_video(metadata)

    def test_too_short(self):
        metadata = VideoMetadata(
            video_id="test123",
            title="Test Video",
            channel="Test Channel",
            duration=5,
            upload_date="20250115",
            description="Too short",
            thumbnail_url="https://example.com/thumb.jpg",
        )
        with pytest.raises(IngestionError, match="too short"):
            validate_video(metadata)


class TestFetchMetadata:
    @patch("core.ingestion.yt_dlp.YoutubeDL")
    def test_success(self, mock_ydl_class):
        mock_ydl = MagicMock()
        mock_ydl_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.return_value = {
            "id": "dQw4w9WgXcQ",
            "title": "Rick Astley - Never Gonna Give You Up",
            "channel": "Rick Astley",
            "duration": 213,
            "upload_date": "20091025",
            "description": "Official music video",
            "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
        }

        metadata = fetch_metadata("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        assert metadata.video_id == "dQw4w9WgXcQ"
        assert metadata.title == "Rick Astley - Never Gonna Give You Up"
        assert metadata.channel == "Rick Astley"
        assert metadata.duration == 213

    @patch("core.ingestion.yt_dlp.YoutubeDL")
    def test_private_video(self, mock_ydl_class):
        mock_ydl = MagicMock()
        mock_ydl_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.side_effect = Exception("Video unavailable")

        with pytest.raises(IngestionError):
            fetch_metadata("https://www.youtube.com/watch?v=private123")


class TestIngest:
    @patch("core.ingestion.download_video")
    @patch("core.ingestion.fetch_metadata")
    def test_success(self, mock_fetch, mock_download, tmp_path):
        mock_fetch.return_value = VideoMetadata(
            video_id="test123",
            title="Test",
            channel="Chan",
            duration=120,
            upload_date="20250101",
            description="Desc",
            thumbnail_url="https://example.com/thumb.jpg",
        )
        mock_download.return_value = tmp_path / "video.mp4"

        result = ingest("https://www.youtube.com/watch?v=test123", tmp_path)

        assert result.metadata.video_id == "test123"
        assert result.video_path == tmp_path / "video.mp4"


class TestExtractAudio:
    @patch("core.ingestion.subprocess.run")
    def test_stream_copy_success(self, mock_run, tmp_path):
        video_path = tmp_path / "test123.mp4"
        video_path.touch()
        audio_path = tmp_path / "test123.m4a"

        def side_effect(cmd, **kwargs):
            # Simulate ffmpeg creating the output file
            audio_path.touch()
            return MagicMock(returncode=0)

        mock_run.side_effect = side_effect

        result = extract_audio(video_path, tmp_path)

        assert result == audio_path
        mock_run.assert_called_once()
        # Verify stream copy was used
        cmd = mock_run.call_args[0][0]
        assert "-acodec" in cmd
        assert "copy" in cmd

    @patch("core.ingestion.subprocess.run")
    def test_fallback_reencode(self, mock_run, tmp_path):
        video_path = tmp_path / "test123.mp4"
        video_path.touch()
        audio_path = tmp_path / "test123.m4a"

        call_count = 0

        def side_effect(cmd, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call (stream copy) fails
                return MagicMock(returncode=1)
            else:
                # Second call (re-encode) succeeds
                audio_path.touch()
                return MagicMock(returncode=0)

        mock_run.side_effect = side_effect

        result = extract_audio(video_path, tmp_path)

        assert result == audio_path
        assert mock_run.call_count == 2
        # Verify second call used re-encoding
        cmd = mock_run.call_args_list[1][0][0]
        assert "aac" in cmd
        assert "128k" in cmd

    @patch("core.ingestion.subprocess.run")
    def test_both_methods_fail(self, mock_run, tmp_path):
        video_path = tmp_path / "test123.mp4"
        video_path.touch()

        mock_run.return_value = MagicMock(returncode=1, stderr="ffmpeg error")

        with pytest.raises(IngestionError, match="Failed to extract audio"):
            extract_audio(video_path, tmp_path)
