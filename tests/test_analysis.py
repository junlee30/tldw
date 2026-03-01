"""Tests for video analysis module."""

import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from prompts.video_analysis import (
    VideoSegment,
    VideoAnalysisResult,
    build_analysis_prompt,
    compute_scene_count,
)
from core.analysis import (
    _save_analysis_cache,
    load_analysis_cache,
    analyze,
)


def _make_segment(**overrides) -> VideoSegment:
    """Helper to create a VideoSegment with defaults."""
    defaults = dict(
        timestamp=65.0,
        timestamp_display="1:05",
        headline="The big reveal",
        narration="The host reveals the main topic. The audience is captivated. Everything changes from here.",
        visual_description="Host standing in front of a whiteboard.",
        transition="But then...",
    )
    defaults.update(overrides)
    return VideoSegment(**defaults)


def _make_result(**overrides) -> VideoAnalysisResult:
    """Helper to create a VideoAnalysisResult with defaults."""
    defaults = dict(
        title_summary="A great video about Python",
        prologue="This is where our story begins. The stage is set for something remarkable.",
        epilogue="And that's how it all came together.",
        language="en",
        segments=[_make_segment(timestamp=10.0, timestamp_display="0:10")],
        thumbnail_timestamp=10.0,
    )
    defaults.update(overrides)
    return VideoAnalysisResult(**defaults)


class TestVideoSegmentModel:
    def test_valid(self):
        segment = _make_segment()
        assert segment.timestamp == 65.0
        assert segment.headline == "The big reveal"
        assert "main topic" in segment.narration
        assert segment.transition == "But then..."

    def test_missing_fields(self):
        with pytest.raises(Exception):
            VideoSegment(timestamp=65.0, headline="Test")

    def test_transition_defaults_empty(self):
        segment = VideoSegment(
            timestamp=10.0,
            timestamp_display="0:10",
            headline="Test",
            narration="Some narration here.",
            visual_description="Visual.",
        )
        assert segment.transition == ""


class TestVideoAnalysisResult:
    def test_valid(self):
        result = _make_result(
            segments=[
                _make_segment(timestamp=10.0, timestamp_display="0:10"),
                _make_segment(timestamp=60.0, timestamp_display="1:00", headline="Main content"),
            ]
        )
        assert len(result.segments) == 2
        assert result.thumbnail_timestamp == 10.0
        assert result.prologue.startswith("This is where")
        assert result.epilogue != ""
        assert result.language == "en"

    def test_language_defaults_to_en(self):
        result = VideoAnalysisResult(
            title_summary="Test",
            prologue="Prologue text.",
            segments=[_make_segment()],
            thumbnail_timestamp=10.0,
        )
        assert result.language == "en"


class TestComputeSceneCount:
    def test_very_short_video_hits_floor(self):
        # 2 min → raw 1, clamped to MIN_SCENES=4
        floor, target = compute_scene_count(120)
        assert target == 4
        assert floor == 4

    def test_short_video(self):
        # 5 min → raw 2.5 → round 2, clamped to 4
        floor, target = compute_scene_count(300)
        assert target == 4
        assert floor == 4

    def test_medium_video(self):
        # 10 min → raw 5 → target 5, floor max(4, round(4.0))=4
        floor, target = compute_scene_count(600)
        assert target == 5
        assert floor == 4

    def test_20_min_video(self):
        # 20 min → raw 10 → target 10, floor max(4, round(8.0))=8
        floor, target = compute_scene_count(1200)
        assert target == 10
        assert floor == 8

    def test_35_min_video(self):
        # 35 min → raw 17.5 → round 18, floor max(4, round(14.4))=14
        floor, target = compute_scene_count(2100)
        assert target == 18
        assert floor == 14

    def test_very_long_video_hits_ceiling(self):
        # 60 min → raw 30, clamped to MAX_SCENES=20, floor max(4, round(16))=16
        floor, target = compute_scene_count(3600)
        assert target == 20
        assert floor == 16

    def test_floor_never_exceeds_target(self):
        for secs in [60, 300, 600, 1200, 2100, 3600]:
            floor, target = compute_scene_count(secs)
            assert floor <= target


class TestBuildAnalysisPrompt:
    def test_includes_duration(self):
        prompt = build_analysis_prompt(300)
        assert "300" in prompt
        assert "5:00" in prompt

    def test_long_duration(self):
        prompt = build_analysis_prompt(3661)
        assert "3661" in prompt
        assert "1:01:01" in prompt

    def test_storyteller_framing(self):
        prompt = build_analysis_prompt(300)
        assert "storyteller" in prompt.lower()
        assert "SAME LANGUAGE" in prompt

    def test_short_video_scene_count_in_prompt(self):
        prompt = build_analysis_prompt(300)
        # 5 min → target 4, floor 4
        assert "4-4" in prompt

    def test_long_video_scene_count_in_prompt(self):
        prompt = build_analysis_prompt(2100)
        # 35 min → target 18, floor 14
        assert "14-18" in prompt

    def test_coverage_language_in_prompt(self):
        prompt = build_analysis_prompt(600)
        assert "retell the entire video" in prompt
        assert "Do NOT skip sections" in prompt


class TestAnalysisCache:
    def test_save_and_load_roundtrip(self, tmp_path):
        result = _make_result()
        _save_analysis_cache(result, tmp_path)
        loaded = load_analysis_cache(tmp_path)

        assert loaded is not None
        assert loaded.title_summary == "A great video about Python"
        assert len(loaded.segments) == 1
        assert loaded.segments[0].timestamp == 10.0
        assert loaded.prologue.startswith("This is where")
        assert loaded.language == "en"

    def test_load_missing_file(self, tmp_path):
        result = load_analysis_cache(tmp_path)
        assert result is None


class TestAnalyze:
    @patch("core.analysis.load_analysis_cache")
    def test_uses_cache(self, mock_load_cache, tmp_path):
        cached = _make_result(title_summary="Cached")
        mock_load_cache.return_value = cached

        result = analyze(tmp_path / "video.mp4", 120, tmp_path)

        assert result.title_summary == "Cached"
        mock_load_cache.assert_called_once_with(tmp_path)
