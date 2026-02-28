"""Configuration constants for TL;DW."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# --- Paths ---
PROJECT_ROOT = Path(__file__).parent
ASSETS_DIR = PROJECT_ROOT / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
OVERLAYS_DIR = ASSETS_DIR / "overlays"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
OUTPUT_DIR = PROJECT_ROOT / "output"

FONT_BOLD = FONTS_DIR / "Inter-Bold.ttf"
FONT_REGULAR = FONTS_DIR / "Inter-Regular.ttf"
WATERMARK_PATH = OVERLAYS_DIR / "tldw_watermark.png"
FAVICON_PATH = ASSETS_DIR / "favicon.ico"

# --- API ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"

# --- Video constraints ---
MAX_VIDEO_DURATION = 3600  # 1 hour in seconds
MIN_VIDEO_DURATION = 10  # 10 seconds minimum

# --- Card dimensions ---
CARD_WIDTH = 1280
CARD_HEIGHT = 720

# --- OG image dimensions ---
OG_WIDTH = 1200
OG_HEIGHT = 630

# --- Frame extraction ---
FRAME_SEARCH_WINDOW = 1.0  # seconds +/- around target timestamp
FRAME_CANDIDATES = 2  # number of candidate frames to evaluate

# --- Gemini File API ---
FILE_UPLOAD_POLL_INTERVAL = 5  # seconds
FILE_UPLOAD_TIMEOUT = 300  # 5 minutes

# --- yt-dlp ---
YTDLP_FORMAT = "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best"
YTDLP_RETRIES = 3

# --- Retry ---
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# --- Scene scaling ---
SCENES_PER_MINUTE = 0.5  # 1 scene per 2 minutes of video
MIN_SCENES = 4           # floor for very short videos
MAX_SCENES = 20          # ceiling for very long videos
