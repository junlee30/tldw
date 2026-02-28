# TL;DW

**Too Long; Didn't Watch** — Convert YouTube videos into shareable visual story summaries.

Given a YouTube URL, TL;DW generates a self-contained HTML page with:
- **Scene cards that scale with video length** (4-20) — frame capture + headline + summary, each linking to that timestamp on YouTube
- **OG thumbnail** (1200x630) for rich link previews on Telegram, X, Slack, etc.
- **Dark-themed responsive page** with scroll animations and proper meta tags

## How It Works

1. **Download** — yt-dlp fetches the video at 720p
2. **Analyze** — Gemini 2.5 Flash watches the video and identifies scenes (count scales with duration) via structured output
3. **Extract** — ffmpeg pulls frames at each timestamp, sharpness scoring picks the best candidate
4. **Compose** — Pillow renders card images with darkened frames, gradient overlays, headlines, and timestamps
5. **Generate** — Jinja2 produces a self-contained HTML page with inlined CSS

Analysis results are cached in `analysis.json` so re-runs skip the API call.

## Setup

### Prerequisites

- Python 3.10+
- ffmpeg on PATH (`winget install ffmpeg` on Windows)
- [Gemini API key](https://aistudio.google.com/apikey)

### Install

```bash
pip install -r requirements.txt
```

Create a `.env` file (see `.env.example`):

```
GEMINI_API_KEY=your-key-here
```

### Font Assets

Download [Inter](https://github.com/rsms/inter/releases) and place `Inter-Bold.ttf` and `Inter-Regular.ttf` in `assets/fonts/`. Then generate the watermark and favicon:

```bash
python generate_assets.py
```

## Usage

### CLI

```bash
python main.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

Options:
- `-v, --verbose` — debug logging
- `--no-open` — don't auto-open in browser

Output goes to `output/<video_id>/`:
```
output/<video_id>/
  index.html          # summary page
  og-thumbnail.png    # social preview image (1200x630)
  analysis.json       # cached Gemini analysis
  cards/              # card images (1280x720 WebP)
  frames/             # extracted raw frames
```

### Web App

A mobile-friendly web UI for submitting URLs, tracking progress, and browsing summaries.

```bash
# Add to .env
TLDW_PASSWORD=your-password
SECRET_KEY=some-random-secret

# Start the server
uvicorn web.app:app --reload --port 8080
```

Open `http://localhost:8080`, log in, paste a YouTube URL, and watch it process.

### Deploy

Hosted on Oracle Cloud Free Tier at [tldwapp.com](https://tldwapp.com). Pushes to `master` auto-deploy via GitHub Actions.

```bash
# Or run locally with Docker
docker build -t tldw .
docker run -d --env-file .env -v ./output:/app/output -p 8080:8080 tldw
```

## Testing

```bash
python -m pytest tests/ -v
```

60 unit tests covering URL parsing, metadata validation, analysis caching, scene count scaling, sharpness computation, text wrapping, card composition, duration formatting, and HTML generation.

## Project Structure

```
tldw/
  main.py                 # CLI entry point
  config.py               # constants and settings
  core/
    ingestion.py           # YouTube download + metadata
    analysis.py            # Gemini video analysis
    extraction.py          # ffmpeg frame extraction + sharpness
    composition.py         # card image rendering
    og_image.py            # OG thumbnail generation
    page_generator.py      # HTML generation
    pipeline.py            # orchestration
  prompts/
    video_analysis.py      # Pydantic models + Gemini prompt
  web/
    app.py                 # FastAPI app
    auth.py                # password auth + session middleware
    db.py                  # SQLite job tracking
    jobs.py                # background worker + progress handler
    routes/
      api.py               # JSON API endpoints
      pages.py             # HTML page routes
    static/
      style.css            # mobile-first dark theme
  templates/
    summary_page.html      # Jinja2 template (CLI output)
    web/                   # web app templates
  assets/
    fonts/                 # Inter Bold + Regular TTFs
    overlays/              # TL;DW watermark
  tests/                   # unit tests
  Dockerfile              # Docker image for deployment
```

## Limitations

- Max video duration: 1 hour (configurable in `config.py`)
- Gemini free tier has rate limits — the tool retries on 429 errors
- Fonts fall back to system default if Inter TTFs are missing
- Korean/non-Latin video titles render correctly in HTML but card images use the bundled Inter font
