"""JSON API endpoints for job management."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.ingestion import extract_video_id
from web.db import create_job, get_job, list_jobs, find_job_by_video_id
from web.jobs import enqueue_job, estimate_total_seconds

router = APIRouter(prefix="/api")


class SubmitRequest(BaseModel):
    youtube_url: str


@router.post("/jobs")
def submit_job(req: SubmitRequest):
    url = req.youtube_url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="youtube_url is required")

    # Extract video_id for duplicate detection
    try:
        video_id = extract_video_id(url)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")

    # Check for existing job with this video_id
    existing = find_job_by_video_id(video_id)
    if existing and existing["status"] in ("pending", "processing", "completed"):
        return existing

    # Create new job
    job = create_job(url, video_id=video_id)
    enqueue_job(job["id"], url)
    return job


@router.get("/jobs")
def get_jobs():
    return list_jobs()


@router.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    result = dict(job)
    if result.get("video_duration", 0) > 0 and result["status"] == "processing":
        result["estimated_seconds"] = estimate_total_seconds(result["video_duration"])
    return result
