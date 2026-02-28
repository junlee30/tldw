"""Video ingestion: download and extract metadata from YouTube videos."""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import yt_dlp

from config import (
    MAX_VIDEO_DURATION,
    MIN_VIDEO_DURATION,
    YTDLP_FORMAT,
    YTDLP_RETRIES,
)

logger = logging.getLogger(__name__)


class IngestionError(Exception):
    """Raised when video ingestion fails."""


@dataclass
class VideoMetadata:
    video_id: str
    title: str
    channel: str
    duration: int
    upload_date: str
    description: str
    thumbnail_url: str


@dataclass
class IngestionResult:
    metadata: VideoMetadata
    video_path: Path


def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from various URL formats."""
    if not url:
        raise ValueError("URL cannot be empty")

    parsed = urlparse(url)

    # youtu.be/VIDEO_ID
    if parsed.hostname in ("youtu.be",):
        video_id = parsed.path.lstrip("/")
        if video_id:
            return video_id.split("/")[0]

    # youtube.com/watch?v=VIDEO_ID
    if parsed.hostname in ("www.youtube.com", "youtube.com", "m.youtube.com"):
        if parsed.path == "/watch":
            qs = parse_qs(parsed.query)
            if "v" in qs:
                return qs["v"][0]

        # youtube.com/shorts/VIDEO_ID, youtube.com/embed/VIDEO_ID, or youtube.com/live/VIDEO_ID
        match = re.match(r"^/(shorts|embed|live)/([a-zA-Z0-9_-]+)", parsed.path)
        if match:
            return match.group(2)

    raise ValueError(f"Could not extract video ID from URL: {url}")


def fetch_metadata(url: str) -> VideoMetadata:
    """Fetch video metadata without downloading the video."""
    opts = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        raise IngestionError(f"Failed to fetch metadata: {e}") from e

    return VideoMetadata(
        video_id=info.get("id", ""),
        title=info.get("title", "Untitled"),
        channel=info.get("channel", info.get("uploader", "Unknown")),
        duration=int(info.get("duration", 0)),
        upload_date=info.get("upload_date", ""),
        description=info.get("description", ""),
        thumbnail_url=info.get("thumbnail", ""),
    )


def validate_video(metadata: VideoMetadata) -> None:
    """Validate that the video meets requirements."""
    if metadata.duration < MIN_VIDEO_DURATION:
        raise IngestionError(
            f"Video is too short ({metadata.duration}s). "
            f"Minimum is {MIN_VIDEO_DURATION}s."
        )
    if metadata.duration > MAX_VIDEO_DURATION:
        raise IngestionError(
            f"Video is too long ({metadata.duration}s). "
            f"Maximum is {MAX_VIDEO_DURATION}s."
        )


def download_video(url: str, output_dir: Path) -> Path:
    """Download video at 720p max quality."""
    output_template = str(output_dir / "%(id)s.%(ext)s")
    opts = {
        "format": YTDLP_FORMAT,
        "outtmpl": output_template,
        "merge_output_format": "mp4",
        "retries": YTDLP_RETRIES,
        "quiet": True,
        "no_warnings": True,
    }

    logger.info("Downloading video...")
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info["id"]
    except Exception as e:
        raise IngestionError(f"Failed to download video: {e}") from e

    # Find the downloaded file
    video_path = output_dir / f"{video_id}.mp4"
    if not video_path.exists():
        # Try to find any video file with that ID
        for f in output_dir.iterdir():
            if f.stem == video_id:
                video_path = f
                break

    if not video_path.exists():
        raise IngestionError("Downloaded video file not found")

    logger.info(f"Downloaded to {video_path}")
    return video_path


def ingest(url: str, output_dir: Path) -> IngestionResult:
    """Full ingestion pipeline: fetch metadata, validate, download."""
    logger.info(f"Ingesting video from {url}")

    metadata = fetch_metadata(url)
    logger.info(f"Video: {metadata.title} ({metadata.duration}s)")

    validate_video(metadata)

    video_path = download_video(url, output_dir)

    return IngestionResult(metadata=metadata, video_path=video_path)
