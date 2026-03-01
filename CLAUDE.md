# TL;DW — YouTube Video Summary Generator

## What This Project Does

Converts YouTube videos into shareable visual story summaries (HTML pages with scene cards, narration, and OG images). Users submit a YouTube URL via the web app or CLI, and the pipeline downloads the video, sends it to Gemini for analysis, extracts key frames, and generates a self-contained summary page.

## Stack

Python 3.12, FastAPI/Uvicorn, Docker, yt-dlp, ffmpeg, Google Gemini 2.5 Flash, Pillow, Jinja2, SQLite

## Project Structure

```
config.py              # All constants and env var loading
main.py                # CLI entry point
core/
  pipeline.py          # 6-step orchestrator: ingest → analyze → extract → compose → og → html
  ingestion.py         # yt-dlp: download video + fetch metadata
  analysis.py          # Gemini: upload video, analyze, cache results as JSON
  extraction.py        # ffmpeg: extract frames at timestamps, pick sharpest (Laplacian)
  composition.py       # Pillow: resize frames to 1280x720 WebP cards
  og_image.py          # Pillow: 1200x630 OG thumbnail with branding overlay
  page_generator.py    # Jinja2: render summary HTML page, metadata persistence
prompts/
  video_analysis.py    # Pydantic models + Gemini prompt template
web/
  app.py               # FastAPI app with auth middleware
  auth.py              # HMAC-SHA256 signed cookie sessions (30-day TTL)
  db.py                # SQLite job tracking
  jobs.py              # Background thread pool (max 1 concurrent), progress via log handler
  routes/
    api.py             # POST /api/jobs, GET /api/jobs, GET /api/jobs/{id}
    pages.py           # /, /login, /jobs/{id}, /s/{video_id}/ (serves generated summaries)
templates/
  summary_page.html    # Self-contained dark-theme summary output
  web/                 # Web app templates (home, login, job status)
assets/                # Fonts (Inter), watermark overlay, favicon
tests/                 # 75+ unit tests (ingestion, analysis, extraction, composition, page gen)
```

## Pipeline Flow

1. **Ingest** — yt-dlp downloads video (480p max), extracts metadata, saves `metadata.json`
2. **Analyze** — Upload to Gemini File API, analyze with structured prompt, cache as `analysis.json`
3. **Extract Frames** — ffmpeg pulls frames at each segment timestamp, picks sharpest
4. **Compose Cards** — Resize frames to 1280x720 WebP
5. **Generate OG Image** — Darken frame + gradient + brand pill + title
6. **Generate HTML** — Jinja2 render with scenes, narration, YouTube timestamp links

Output goes to `output/{video_id}/` (index.html, metadata.json, og-thumbnail.png, cards/, frames/, analysis.json).

**Dynamic rendering:** The web app renders summary pages dynamically from `metadata.json` + `analysis.json` on each request, so template changes apply to all summaries without regeneration. CLI still produces standalone `index.html`. Old output dirs without `metadata.json` fall back to serving the static `index.html`.

## Environment Variables (.env)

```
GEMINI_API_KEY=...                          # Required
TLDW_PASSWORD=...                           # Web app login password
SECRET_KEY=...                              # Session cookie signing key
YTDLP_COOKIES_FILE=cookies.txt              # Netscape-format YouTube cookies
DATABASE_PATH=/path/to/tldw.db              # SQLite (defaults to output/tldw.db)
```

## yt-dlp YouTube Auth

YouTube requires cookie auth + JS challenge solving. Three things must be in place:
- **cookies.txt** — Netscape-format cookies exported from browser (in .gitignore, never commit)
- **Node.js** — Installed in Docker image for n-parameter challenge solving
- **yt-dlp-ejs** — Challenge solver scripts (Python package)
- **`js_runtimes: {"node": {}}`** — Must be explicitly passed in yt-dlp opts (defaults to deno which isn't installed)

Cookies expire periodically. Re-export from browser and re-upload to server.

## Deployment

- **Hosting:** Oracle Cloud Free Tier (VM.Standard.E2.1.Micro, 1 OCPU, 1GB RAM, 4GB swap)
- **Server:** `ssh -i ~/.ssh/oracle_tldw ubuntu@167.234.208.79`
- **App dir:** `/opt/tldw/app` (git clone), persistent data at `/opt/tldw/output`
- **Reverse proxy:** Caddy on ports 80/443 → localhost:8080, auto Let's Encrypt
- **Domain:** https://tldwapp.com (Cloudflare DNS, grey cloud / DNS only)
- **CI/CD:** GitHub Actions (`.github/workflows/deploy.yml`) — push to master triggers SSH deploy
- **Docker:** `python:3.12-slim` + ffmpeg + nodejs, env from `/opt/tldw/.env`, volumes for output + cookies.txt
- **No docker-compose** — uses `docker run` directly (docker-compose-plugin unavailable on Ubuntu 22.04)

## Running Tests

```bash
python -m pytest tests/ -v
```

## Running Locally

```bash
# CLI
python main.py "https://youtu.be/VIDEO_ID"

# Web app
uvicorn web.app:app --host 0.0.0.0 --port 8080
```

## Key Config Values (config.py)

- Video: 10s min, 3600s (1hr) max duration
- Download: 480p max quality
- Cards: 1280x720, WebP quality 90
- OG image: 1200x630 PNG
- Scenes: 1 per 2 min of video (min 4, max 20)
- Gemini upload: 5s poll interval, 5min timeout
- Retries: 3 attempts, 2s delay (30s × attempt for rate limits)
- Web auth: 30-day session TTL, max 1 concurrent pipeline job
