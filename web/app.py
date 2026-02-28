"""FastAPI application factory."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from web.auth import AuthMiddleware
from web.routes.api import router as api_router
from web.routes.pages import router as pages_router

app = FastAPI(title="TL;DW", docs_url=None, redoc_url=None)

# Auth middleware
app.add_middleware(AuthMiddleware)

# Static files
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Routes
app.include_router(api_router)
app.include_router(pages_router)
