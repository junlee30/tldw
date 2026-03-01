"""HTML page routes and summary file serving."""

from pathlib import Path

from fastapi import APIRouter, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates

from config import OUTPUT_DIR, TEMPLATES_DIR
from core.analysis import load_analysis_cache
from core.page_generator import load_metadata, render_summary_html
from web.auth import verify_password, create_session_token, COOKIE_NAME
from web.db import get_job, list_jobs, find_job_by_video_id

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("web/login.html", {"request": request})


@router.post("/auth/login")
async def do_login(password: str = Form(...)):
    if not verify_password(password):
        return RedirectResponse(url="/login?error=1", status_code=302)
    token = create_session_token()
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=60 * 60 * 24 * 30,
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/auth/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(COOKIE_NAME)
    return response


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    jobs = list_jobs()
    # Find completed jobs that have output directories
    summaries = []
    for job in jobs:
        if job["status"] == "completed" and job["video_id"]:
            output_dir = OUTPUT_DIR / job["video_id"]
            if (output_dir / "index.html").exists():
                # Try to get thumbnail path
                thumbnail = None
                og_thumb = output_dir / "og-thumbnail.png"
                if og_thumb.exists():
                    thumbnail = f"/s/{job['video_id']}/og-thumbnail.png"
                summaries.append({
                    **job,
                    "thumbnail": thumbnail,
                })
    return templates.TemplateResponse("web/home.html", {
        "request": request,
        "summaries": summaries,
        "jobs": [j for j in jobs if j["status"] in ("pending", "processing")],
    })


@router.get("/jobs/{job_id}", response_class=HTMLResponse)
async def job_status_page(request: Request, job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return templates.TemplateResponse("web/job_status.html", {
        "request": request,
        "job": job,
    })


@router.get("/s/{video_id}/")
async def serve_summary(video_id: str):
    output_dir = OUTPUT_DIR / video_id
    if not output_dir.is_dir():
        raise HTTPException(status_code=404, detail="Summary not found")

    # Try dynamic rendering with metadata + analysis
    metadata = load_metadata(output_dir)
    analysis = load_analysis_cache(output_dir)
    if metadata is not None and analysis is not None:
        html = render_summary_html(metadata, analysis, output_dir)
        return HTMLResponse(html)

    # Fallback: serve static index.html for old output dirs
    html_path = output_dir / "index.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="Summary not found")
    html = html_path.read_text(encoding="utf-8")
    # Patch older summaries: make brand badge a home link
    if '<div class="brand">' in html:
        html = html.replace(
            '<div class="brand">TL;DW</div>',
            '<a href="/" class="brand">TL;DW</a>',
            1,
        )
        html = html.replace(
            "margin-bottom: 24px;\n        }",
            "margin-bottom: 24px;\n            text-decoration: none;\n            transition: background 0.2s;\n        }\n\n        .brand:hover {\n            background: #e0e0e0;\n        }",
            1,
        )
    return HTMLResponse(html)


@router.get("/s/{video_id}/{path:path}")
async def serve_summary_asset(video_id: str, path: str):
    file_path = OUTPUT_DIR / video_id / path
    # Security: ensure the resolved path is inside the output directory
    try:
        file_path.resolve().relative_to(OUTPUT_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)
