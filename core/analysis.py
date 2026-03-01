"""Video analysis using Gemini API."""

import json
import logging
import time
from pathlib import Path

from google import genai
from google.genai import types

from google.genai.errors import ClientError

from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    FILE_UPLOAD_POLL_INTERVAL,
    FILE_UPLOAD_TIMEOUT,
    MAX_RETRIES,
)
from prompts.video_analysis import (
    VideoAnalysisResult,
    build_analysis_prompt,
    build_audio_analysis_prompt,
)

logger = logging.getLogger(__name__)

CACHE_FILENAME = "analysis.json"


def _create_client() -> genai.Client:
    """Create a Gemini API client."""
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY not set. Add it to your .env file."
        )
    return genai.Client(api_key=GEMINI_API_KEY)


def _upload_video(client: genai.Client, video_path: Path):
    """Upload video via Gemini File API and wait until ACTIVE."""
    logger.info(f"Uploading {video_path.name} to Gemini File API...")

    uploaded = client.files.upload(file=video_path)
    logger.info(f"Upload started: {uploaded.name}")

    start = time.time()
    while uploaded.state == "PROCESSING":
        if time.time() - start > FILE_UPLOAD_TIMEOUT:
            raise TimeoutError(
                f"File processing timed out after {FILE_UPLOAD_TIMEOUT}s"
            )
        time.sleep(FILE_UPLOAD_POLL_INTERVAL)
        uploaded = client.files.get(name=uploaded.name)
        logger.debug(f"File state: {uploaded.state}")

    if uploaded.state == "FAILED":
        raise RuntimeError(f"File processing failed: {uploaded.name}")

    logger.info("File ready for analysis")
    return uploaded


def _analyze_video(
    client: genai.Client, uploaded_file, duration: int, audio_only: bool = False
) -> VideoAnalysisResult:
    """Run Gemini analysis on the uploaded file (video or audio)."""
    if audio_only:
        prompt = build_audio_analysis_prompt(duration)
    else:
        prompt = build_analysis_prompt(duration)

    logger.info("Analyzing video with Gemini...")

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[
                    types.Content(
                        parts=[
                            types.Part.from_uri(
                                file_uri=uploaded_file.uri,
                                mime_type=uploaded_file.mime_type,
                            ),
                            types.Part.from_text(text=prompt),
                        ],
                    ),
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=VideoAnalysisResult,
                ),
            )

            result = VideoAnalysisResult.model_validate_json(response.text)
            logger.info(f"Analysis complete: {len(result.segments)} segments found")
            return result

        except ClientError as e:
            last_error = e
            if e.code == 429 and attempt < MAX_RETRIES:
                wait = 30 * attempt
                logger.warning(
                    f"Rate limited (attempt {attempt}/{MAX_RETRIES}), "
                    f"waiting {wait}s..."
                )
                time.sleep(wait)
            else:
                raise

    raise last_error


def _save_analysis_cache(result: VideoAnalysisResult, output_dir: Path) -> None:
    """Save analysis result to JSON cache."""
    cache_path = output_dir / CACHE_FILENAME
    cache_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    logger.debug(f"Analysis cached to {cache_path}")


def load_analysis_cache(output_dir: Path) -> VideoAnalysisResult | None:
    """Load analysis result from JSON cache if it exists."""
    cache_path = output_dir / CACHE_FILENAME
    if not cache_path.exists():
        return None

    try:
        data = cache_path.read_text(encoding="utf-8")
        result = VideoAnalysisResult.model_validate_json(data)
        logger.info("Loaded analysis from cache")
        return result
    except Exception as e:
        logger.warning(f"Failed to load cache: {e}")
        return None


def _cleanup_uploaded_file(client: genai.Client, uploaded_file) -> None:
    """Delete uploaded file from Gemini servers."""
    try:
        client.files.delete(name=uploaded_file.name)
        logger.debug("Cleaned up uploaded file")
    except Exception as e:
        logger.warning(f"Failed to cleanup uploaded file: {e}")


def analyze(
    file_path: Path, duration: int, output_dir: Path, audio_only: bool = False
) -> VideoAnalysisResult:
    """Main analysis entry point: cache check -> upload -> analyze -> cache -> cleanup."""
    # Check cache first
    cached = load_analysis_cache(output_dir)
    if cached is not None:
        return cached

    client = _create_client()

    uploaded_file = _upload_video(client, file_path)
    try:
        result = _analyze_video(client, uploaded_file, duration, audio_only=audio_only)
        if audio_only:
            result.audio_only = True
        _save_analysis_cache(result, output_dir)
        return result
    finally:
        _cleanup_uploaded_file(client, uploaded_file)
