"""Tests for core.page_generator module."""

import pytest
from pathlib import Path

from core.page_generator import (
    _format_duration,
    _format_date,
    _build_youtube_timestamp_url,
    _build_template_context,
    generate_page,
)
from core.ingestion import VideoMetadata
from prompts.video_analysis import VideoSegment, VideoAnalysisResult


class TestFormatDuration:
    def test_short(self):
        assert _format_duration(65) == "1:05"

    def test_long(self):
        assert _format_duration(3661) == "1:01:01"

    def test_zero(self):
        assert _format_duration(0) == "0:00"

    def test_exact_minute(self):
        assert _format_duration(60) == "1:00"

    def test_under_minute(self):
        assert _format_duration(45) == "0:45"


class TestFormatDate:
    def test_standard(self):
        assert _format_date("20250115") == "Jan 15, 2025"

    def test_different_month(self):
        assert _format_date("20231225") == "Dec 25, 2023"

    def test_empty(self):
        assert _format_date("") == ""

    def test_invalid(self):
        assert _format_date("not-a-date") == "not-a-date"


class TestBuildYoutubeTimestampUrl:
    def test_standard(self):
        url = _build_youtube_timestamp_url("dQw4w9WgXcQ", 65.0)
        assert url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=65"

    def test_zero(self):
        url = _build_youtube_timestamp_url("abc123", 0)
        assert url == "https://www.youtube.com/watch?v=abc123&t=0"


class TestGeneratePage:
    def _make_test_data(self, tmp_path):
        metadata = VideoMetadata(
            video_id="test123",
            title="Test Video Title",
            channel="Test Channel",
            duration=300,
            upload_date="20250115",
            description="A test video about testing",
            thumbnail_url="https://example.com/thumb.jpg",
        )
        analysis = VideoAnalysisResult(
            title_summary="A great test video",
            prologue="This is where our story begins. The stage is set for something remarkable.",
            epilogue="And that's how it all came together in the end.",
            language="en",
            segments=[
                VideoSegment(
                    timestamp=10.0,
                    timestamp_display="0:10",
                    headline="Introduction",
                    narration="The host introduces the topic with flair. The audience leans in.",
                    visual_description="Title card.",
                    transition="",
                ),
                VideoSegment(
                    timestamp=120.0,
                    timestamp_display="2:00",
                    headline="Main Point",
                    narration="The key argument is presented with conviction. Evidence mounts.",
                    visual_description="Presenter at whiteboard.",
                    transition="But then...",
                ),
            ],
            thumbnail_timestamp=10.0,
        )
        # Create dummy card files
        cards_dir = tmp_path / "cards"
        cards_dir.mkdir()
        cards = []
        for i in range(2):
            card_path = cards_dir / f"card-{i:02d}.webp"
            card_path.write_bytes(b"fake webp data")
            cards.append(card_path)

        og_path = tmp_path / "og-thumbnail.png"
        og_path.write_bytes(b"fake png data")

        return metadata, analysis, cards, og_path

    def test_contains_og_tags(self, tmp_path):
        metadata, analysis, cards, og_path = self._make_test_data(tmp_path)

        html_path = generate_page(metadata, analysis, cards, og_path, tmp_path)

        html = html_path.read_text(encoding="utf-8")
        assert 'og:title' in html
        assert 'og:description' in html
        assert 'og:image' in html
        assert 'twitter:card' in html

    def test_contains_scenes(self, tmp_path):
        metadata, analysis, cards, og_path = self._make_test_data(tmp_path)

        html_path = generate_page(metadata, analysis, cards, og_path, tmp_path)

        html = html_path.read_text(encoding="utf-8")
        assert "Introduction" in html
        assert "Main Point" in html
        assert "card-00.webp" in html

    def test_contains_prologue_and_epilogue(self, tmp_path):
        metadata, analysis, cards, og_path = self._make_test_data(tmp_path)

        html_path = generate_page(metadata, analysis, cards, og_path, tmp_path)

        html = html_path.read_text(encoding="utf-8")
        assert "Prologue" in html
        assert "story begins" in html
        assert "Epilogue" in html
        assert "came together" in html

    def test_contains_transition(self, tmp_path):
        metadata, analysis, cards, og_path = self._make_test_data(tmp_path)

        html_path = generate_page(metadata, analysis, cards, og_path, tmp_path)

        html = html_path.read_text(encoding="utf-8")
        assert "But then..." in html

    def test_language_attribute(self, tmp_path):
        metadata, analysis, cards, og_path = self._make_test_data(tmp_path)

        html_path = generate_page(metadata, analysis, cards, og_path, tmp_path)

        html = html_path.read_text(encoding="utf-8")
        assert 'lang="en"' in html

    def test_reading_time_in_context(self, tmp_path):
        metadata, analysis, cards, og_path = self._make_test_data(tmp_path)

        context = _build_template_context(
            metadata, analysis, cards, "og-thumbnail.png", tmp_path
        )
        assert "reading_time" in context
        assert "min read" in context["reading_time"]

    def test_reading_time_displayed_in_html(self, tmp_path):
        metadata, analysis, cards, og_path = self._make_test_data(tmp_path)

        html_path = generate_page(metadata, analysis, cards, og_path, tmp_path)
        html = html_path.read_text(encoding="utf-8")
        assert "min read" in html

    def test_scene_counter_badges(self, tmp_path):
        metadata, analysis, cards, og_path = self._make_test_data(tmp_path)

        html_path = generate_page(metadata, analysis, cards, og_path, tmp_path)
        html = html_path.read_text(encoding="utf-8")
        assert "1 / 2" in html
        assert "2 / 2" in html
        assert "scene-counter" in html

    def test_scene_ids(self, tmp_path):
        metadata, analysis, cards, og_path = self._make_test_data(tmp_path)

        html_path = generate_page(metadata, analysis, cards, og_path, tmp_path)
        html = html_path.read_text(encoding="utf-8")
        assert 'id="scene-1"' in html
        assert 'id="scene-2"' in html

    def test_scroll_progress_bar(self, tmp_path):
        metadata, analysis, cards, og_path = self._make_test_data(tmp_path)

        html_path = generate_page(metadata, analysis, cards, og_path, tmp_path)
        html = html_path.read_text(encoding="utf-8")
        assert "scroll-progress" in html

    def test_back_to_top_button(self, tmp_path):
        metadata, analysis, cards, og_path = self._make_test_data(tmp_path)

        html_path = generate_page(metadata, analysis, cards, og_path, tmp_path)
        html = html_path.read_text(encoding="utf-8")
        assert "back-to-top" in html

    def test_sticky_bottom_bar(self, tmp_path):
        metadata, analysis, cards, og_path = self._make_test_data(tmp_path)

        html_path = generate_page(metadata, analysis, cards, og_path, tmp_path)
        html = html_path.read_text(encoding="utf-8")
        assert "sticky-bar" in html

    def test_toc_not_shown_for_few_scenes(self, tmp_path):
        """TOC should not render when there are fewer than 8 scenes."""
        metadata, analysis, cards, og_path = self._make_test_data(tmp_path)

        html_path = generate_page(metadata, analysis, cards, og_path, tmp_path)
        html = html_path.read_text(encoding="utf-8")
        # Only 2 scenes in test data, TOC HTML elements should not appear
        assert "Jump to scene" not in html
        assert 'id="toc"' not in html

    def test_toc_shown_for_many_scenes(self, tmp_path):
        """TOC should render when there are 8 or more scenes."""
        metadata, analysis, cards, og_path = self._make_test_data(tmp_path)

        # Add more segments to reach 8
        for i in range(6):
            analysis.segments.append(VideoSegment(
                timestamp=float(180 + i * 60),
                timestamp_display=f"{3 + i}:00",
                headline=f"Scene {i + 3}",
                narration=f"Narration for scene {i + 3}.",
                visual_description="Visual.",
                transition="Meanwhile...",
            ))
            card_path = tmp_path / "cards" / f"card-{i + 2:02d}.webp"
            card_path.write_bytes(b"fake webp data")
            cards.append(card_path)

        html_path = generate_page(metadata, analysis, cards, og_path, tmp_path)
        html = html_path.read_text(encoding="utf-8")
        assert "toc-toggle" in html
        assert "Jump to scene" in html

    def test_reading_time_minimum_one_minute(self, tmp_path):
        """Reading time should be at least 1 min even for very short content."""
        metadata, analysis, cards, og_path = self._make_test_data(tmp_path)

        context = _build_template_context(
            metadata, analysis, cards, "og-thumbnail.png", tmp_path
        )
        assert context["reading_time"] == "1 min read"
