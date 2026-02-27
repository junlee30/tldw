"""Tests for video analysis module."""

import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from prompts.video_analysis import (
    VideoSegment,
    VideoAnalysisResult,
    build_analysis_prompt,
)
from core.analysis import (
    _save_analysis_cache,
    _load_analysis_cache,
    analyze,
)


class TestVideoSegmentModel:
    def test_valid(self):
        segment = VideoSegment(
            timestamp=65.0,
            timestamp_display="1:05",
            headline="The big reveal",
            summary="The host reveals the main topic of the video.",
            visual_description="Host standing in front of a whiteboard.",
        )
        assert segment.timestamp == 65.0
        assert segment.headline == "The big reveal"

    def test_missing_fields(self):
        with pytest.raises(Exception):
            VideoSegment(timestamp=65.0, headline="Test")


class TestVideoAnalysisResult:
    def test_valid(self):
        result = VideoAnalysisResult(
            title_summary="A great video about Python",
            overall_summary="This video covers Python basics.",
            segments=[
                VideoSegment(
                    timestamp=10.0,
                    timestamp_display="0:10",
                    headline="Introduction",
                    summary="The host introduces the topic.",
                    visual_description="Title card with logo.",
                ),
                VideoSegment(
                    timestamp=60.0,
                    timestamp_display="1:00",
                    headline="Main content",
                    summary="Deep dive into the subject.",
                    visual_description="Code editor on screen.",
                ),
            ],
            thumbnail_timestamp=10.0,
        )
        assert len(result.segments) == 2
        assert result.thumbnail_timestamp == 10.0


class TestBuildAnalysisPrompt:
    def test_includes_duration(self):
        prompt = build_analysis_prompt(300)
        assert "300" in prompt
        assert "5:00" in prompt

    def test_long_duration(self):
        prompt = build_analysis_prompt(3661)
        assert "3661" in prompt
        assert "1:01:01" in prompt


class TestAnalysisCache:
    def test_save_and_load_roundtrip(self, tmp_path):
        result = VideoAnalysisResult(
            title_summary="Test summary",
            overall_summary="Overview text.",
            segments=[
                VideoSegment(
                    timestamp=10.0,
                    timestamp_display="0:10",
                    headline="Test",
                    summary="Test summary.",
                    visual_description="Test visual.",
                ),
            ],
            thumbnail_timestamp=10.0,
        )
        _save_analysis_cache(result, tmp_path)
        loaded = _load_analysis_cache(tmp_path)

        assert loaded is not None
        assert loaded.title_summary == "Test summary"
        assert len(loaded.segments) == 1
        assert loaded.segments[0].timestamp == 10.0

    def test_load_missing_file(self, tmp_path):
        result = _load_analysis_cache(tmp_path)
        assert result is None


class TestAnalyze:
    @patch("core.analysis._load_analysis_cache")
    def test_uses_cache(self, mock_load_cache, tmp_path):
        cached = VideoAnalysisResult(
            title_summary="Cached",
            overall_summary="From cache.",
            segments=[
                VideoSegment(
                    timestamp=5.0,
                    timestamp_display="0:05",
                    headline="Cached",
                    summary="Cached segment.",
                    visual_description="Cached visual.",
                ),
            ],
            thumbnail_timestamp=5.0,
        )
        mock_load_cache.return_value = cached

        result = analyze(tmp_path / "video.mp4", 120, tmp_path)

        assert result.title_summary == "Cached"
        mock_load_cache.assert_called_once_with(tmp_path)
