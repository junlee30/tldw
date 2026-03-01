"""Background job worker with progress tracking via log handler."""

import logging
import threading
from datetime import datetime, timezone

from web.db import update_job

# Semaphore: only 1 pipeline job at a time (Gemini rate limits)
_semaphore = threading.Semaphore(1)


class JobProgressHandler(logging.Handler):
    """Captures 'Step N/6: ...' log messages and writes them to the DB."""

    def __init__(self, job_id: str):
        super().__init__()
        self.job_id = job_id

    def emit(self, record: logging.LogRecord):
        msg = record.getMessage()
        if msg.startswith("Step "):
            try:
                update_job(self.job_id, step=msg)
            except Exception:
                pass
        elif msg.startswith("video_duration:"):
            try:
                duration = int(msg.split(":", 1)[1])
                update_job(self.job_id, video_duration=duration)
            except (ValueError, Exception):
                pass


def estimate_total_seconds(video_duration: int) -> int:
    """Estimate total processing time based on video duration.

    Formula: ~2x video duration + 25s overhead for steps 3-6.
    """
    estimate = 2.0 * video_duration + 25
    return max(int(estimate), 30)


def _run_job(job_id: str, youtube_url: str) -> None:
    """Run the pipeline in a background thread."""
    from core.pipeline import run_pipeline, PipelineError
    from core.ingestion import extract_video_id

    # Attach progress handler to the pipeline logger
    pipeline_logger = logging.getLogger("core.pipeline")
    pipeline_logger.setLevel(logging.INFO)
    handler = JobProgressHandler(job_id)
    handler.setLevel(logging.INFO)
    pipeline_logger.addHandler(handler)

    _semaphore.acquire()
    try:
        update_job(job_id, status="processing", step="Step 1/6: Downloading video...")

        # Extract video_id for DB metadata
        try:
            video_id = extract_video_id(youtube_url)
            update_job(job_id, video_id=video_id)
        except ValueError:
            pass

        result = run_pipeline(youtube_url)

        update_job(
            job_id,
            status="completed",
            step="",
            video_id=result.video_id,
            video_title=result.metadata.title,
            thumbnail_url=result.metadata.thumbnail_url,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        logging.getLogger(__name__).exception(f"Job {job_id} failed: {e}")
        update_job(
            job_id,
            status="failed",
            error=str(e),
            step="",
        )
    finally:
        pipeline_logger.removeHandler(handler)
        _semaphore.release()


def enqueue_job(job_id: str, youtube_url: str) -> None:
    """Start a pipeline job in a background thread."""
    t = threading.Thread(target=_run_job, args=(job_id, youtube_url), daemon=True)
    t.start()
