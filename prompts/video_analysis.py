"""Pydantic models and prompt templates for Gemini video analysis."""

from pydantic import BaseModel, Field

from config import MIN_SEGMENTS, MAX_SEGMENTS


class VideoSegment(BaseModel):
    """A key moment in the video."""
    timestamp: float = Field(description="Timestamp in seconds from the start of the video")
    timestamp_display: str = Field(description="Human-readable timestamp like '1:23' or '1:01:05'")
    headline: str = Field(description="Short punchy headline for this moment (max 8 words)")
    summary: str = Field(description="2-3 sentence summary of what happens at this moment")
    visual_description: str = Field(description="Brief description of what's visually happening on screen")


class VideoAnalysisResult(BaseModel):
    """Complete analysis of a video."""
    title_summary: str = Field(description="One-line summary of the entire video (max 15 words)")
    overall_summary: str = Field(description="2-3 sentence overview of the video content")
    segments: list[VideoSegment] = Field(
        description=f"List of {MIN_SEGMENTS}-{MAX_SEGMENTS} key moments from the video"
    )
    thumbnail_timestamp: float = Field(
        description="Timestamp in seconds for the best thumbnail frame "
        "(most visually interesting moment)"
    )


ANALYSIS_PROMPT = """\
You are analyzing a video to create a visual story summary. Your job is to identify the \
{min_segments}-{max_segments} most important and visually interesting moments in this video.

The video is {duration_display} long ({duration_seconds} seconds total).

For each key moment you select:
1. Choose timestamps that are SPREAD across the entire video duration — don't cluster them
2. Prioritize moments with strong visual content (action, expressions, graphics, demos)
3. Write a short, punchy headline (max 8 words) that captures the essence
4. Write a 2-3 sentence summary explaining what happens
5. Describe what's visually on screen at that moment

Also:
- Write a one-line summary of the entire video (max 15 words)
- Write a 2-3 sentence overview of the video
- Pick the single most visually interesting timestamp for the thumbnail

IMPORTANT RULES:
- Timestamps must be valid (between 0 and {duration_seconds})
- Space segments roughly evenly across the video duration
- Headlines should be engaging and specific, not generic
- Summaries should be informative even without watching the video
- Pick {min_segments}-{max_segments} segments total
"""


def build_analysis_prompt(duration_seconds: int) -> str:
    """Build the analysis prompt with duration injected."""
    hours = duration_seconds // 3600
    minutes = (duration_seconds % 3600) // 60
    seconds = duration_seconds % 60

    if hours > 0:
        duration_display = f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        duration_display = f"{minutes}:{seconds:02d}"

    return ANALYSIS_PROMPT.format(
        duration_seconds=duration_seconds,
        duration_display=duration_display,
        min_segments=MIN_SEGMENTS,
        max_segments=MAX_SEGMENTS,
    )
