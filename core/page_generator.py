"""HTML page generation using Jinja2 templates."""

import logging
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from config import TEMPLATES_DIR
from core.ingestion import VideoMetadata
from prompts.video_analysis import VideoAnalysisResult

logger = logging.getLogger(__name__)


def _format_duration(seconds: int) -> str:
    """Format seconds into human-readable duration."""
    if seconds <= 0:
        return "0:00"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _format_date(date_str: str) -> str:
    """Format YYYYMMDD date string to human-readable format."""
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(date_str, "%Y%m%d")
        return dt.strftime("%b %d, %Y")
    except ValueError:
        return date_str


def _build_youtube_timestamp_url(video_id: str, timestamp: float) -> str:
    """Build a YouTube URL that jumps to a specific timestamp."""
    return f"https://www.youtube.com/watch?v={video_id}&t={int(timestamp)}"


def _build_template_context(
    metadata: VideoMetadata,
    analysis: VideoAnalysisResult,
    card_paths: list[Path],
    og_filename: str,
    output_dir: Path,
) -> dict:
    """Build the context dictionary for the Jinja2 template."""
    scenes = []
    for i, (card_path, segment) in enumerate(
        zip(card_paths, analysis.segments)
    ):
        # Use relative path from output dir
        rel_path = card_path.relative_to(output_dir)
        scenes.append({
            "image_path": str(rel_path).replace("\\", "/"),
            "headline": segment.headline,
            "narration": segment.narration,
            "transition": segment.transition if i > 0 else "",
            "timestamp_display": segment.timestamp_display,
            "youtube_url": _build_youtube_timestamp_url(
                metadata.video_id, segment.timestamp
            ),
            "index": i + 1,
            "total": len(card_paths),
        })

    # Compute reading time estimate
    word_count = len(analysis.prologue.split())
    for seg in analysis.segments:
        word_count += len(seg.narration.split())
        word_count += len(seg.headline.split())
    if analysis.epilogue:
        word_count += len(analysis.epilogue.split())
    reading_minutes = max(1, round(word_count / 200))

    return {
        "title": metadata.title,
        "channel": metadata.channel,
        "duration": _format_duration(metadata.duration),
        "upload_date": _format_date(metadata.upload_date),
        "description": metadata.description[:200],
        "title_summary": analysis.title_summary,
        "prologue": analysis.prologue,
        "epilogue": analysis.epilogue,
        "language": analysis.language,
        "scenes": scenes,
        "og_image": og_filename,
        "video_url": f"https://www.youtube.com/watch?v={metadata.video_id}",
        "video_id": metadata.video_id,
        "thumbnail_url": metadata.thumbnail_url,
        "reading_time": f"{reading_minutes} min read",
    }


def generate_page(
    metadata: VideoMetadata,
    analysis: VideoAnalysisResult,
    card_paths: list[Path],
    og_path: Path,
    output_dir: Path,
) -> Path:
    """Generate the HTML summary page."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
    )
    template = env.get_template("summary_page.html")

    og_filename = og_path.name
    context = _build_template_context(
        metadata, analysis, card_paths, og_filename, output_dir
    )

    html = template.render(**context)
    output_path = output_dir / "index.html"
    output_path.write_text(html, encoding="utf-8")

    logger.info(f"HTML page generated: {output_path}")
    return output_path
