"""Main pipeline orchestrating all TL;DW steps."""

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from config import OUTPUT_DIR
from core.ingestion import ingest, extract_video_id, IngestionError, VideoMetadata
from core.analysis import analyze
from core.extraction import extract_frames
from core.composition import compose_all_cards
from core.og_image import generate_og_image
from core.page_generator import generate_page, save_metadata
from prompts.video_analysis import VideoAnalysisResult

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    """Raised when the pipeline fails."""


@dataclass
class PipelineResult:
    video_id: str
    output_dir: Path
    html_path: Path
    og_path: Path
    card_paths: list[Path]
    metadata: VideoMetadata
    analysis: VideoAnalysisResult


def run_pipeline(youtube_url: str) -> PipelineResult:
    """Run the full TL;DW pipeline.

    Steps:
        1. Extract video_id, create output dir
        2. Ingest (download + metadata)
        3. Analyze (Gemini)
        4. Extract frames
        5. Compose cards
        6. Generate OG image
        7. Generate HTML page
        8. Cleanup downloaded video
    """
    # Step 1: Extract video ID and set up output directory
    try:
        video_id = extract_video_id(youtube_url)
    except ValueError as e:
        raise PipelineError(f"Invalid YouTube URL: {e}") from e

    output_dir = OUTPUT_DIR / video_id
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")

    # Step 2: Ingest
    logger.info("Step 1/6: Downloading video...")
    try:
        result = ingest(youtube_url, output_dir)
    except IngestionError as e:
        raise PipelineError(f"Ingestion failed: {e}") from e

    metadata = result.metadata
    video_path = result.video_path
    save_metadata(metadata, output_dir)

    try:
        # Step 3: Analyze
        logger.info("Step 2/6: Analyzing video with AI...")
        analysis = analyze(video_path, metadata.duration, output_dir)

        # Step 4: Extract frames
        logger.info("Step 3/6: Extracting key frames...")
        timestamps = [seg.timestamp for seg in analysis.segments]
        card_frames, thumbnail_frame = extract_frames(
            video_path, timestamps, analysis.thumbnail_timestamp, output_dir
        )

        if not card_frames:
            raise PipelineError("No frames could be extracted")

        # Match frames to segments (skip segments where extraction failed)
        matched_segments = analysis.segments[:len(card_frames)]

        # Step 5: Compose cards
        logger.info("Step 4/6: Composing card images...")
        card_paths = compose_all_cards(card_frames, output_dir)

        # Step 6: Generate OG image
        logger.info("Step 5/6: Generating social preview image...")
        og_path = output_dir / "og-thumbnail.png"
        best_thumbnail = thumbnail_frame or card_frames[0]
        generate_og_image(best_thumbnail, metadata.title, og_path)

        # Step 7: Generate HTML page
        logger.info("Step 6/6: Generating summary page...")
        html_path = generate_page(
            metadata, analysis, card_paths, og_path, output_dir
        )

    finally:
        # Step 8: Cleanup downloaded video
        if video_path.exists():
            try:
                video_path.unlink()
                logger.debug(f"Cleaned up video file: {video_path}")
            except OSError:
                logger.warning(f"Could not delete video file: {video_path}")

    logger.info(f"Done! Open {html_path}")

    return PipelineResult(
        video_id=video_id,
        output_dir=output_dir,
        html_path=html_path,
        og_path=og_path,
        card_paths=card_paths,
        metadata=metadata,
        analysis=analysis,
    )
