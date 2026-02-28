"""Password authentication with signed cookies."""

import hashlib
import hmac
import secrets
import time

from fastapi import Request, Response
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from config import TLDW_PASSWORD, SECRET_KEY

COOKIE_NAME = "tldw_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 days

# Paths that don't require auth
PUBLIC_PATHS = {"/login", "/auth/login"}


def _sign(payload: str) -> str:
    sig = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def _verify_signature(token: str) -> str | None:
    if "." not in token:
        return None
    parts = token.rsplit(".", 1)
    if len(parts) != 2:
        return None
    payload, sig = parts
    expected = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if hmac.compare_digest(sig, expected):
        return payload
    return None


def create_session_token() -> str:
    payload = f"{secrets.token_hex(16)}:{int(time.time())}"
    return _sign(payload)


def verify_session(token: str) -> bool:
    payload = _verify_signature(token)
    if payload is None:
        return False
    parts = payload.split(":")
    if len(parts) != 2:
        return False
    try:
        created = int(parts[1])
    except ValueError:
        return False
    return (time.time() - created) < SESSION_MAX_AGE


def verify_password(password: str) -> bool:
    if not TLDW_PASSWORD:
        return False
    return hmac.compare_digest(password, TLDW_PASSWORD)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Allow public paths and static files
        if path in PUBLIC_PATHS or path.startswith("/static"):
            return await call_next(request)

        # Check session cookie
        token = request.cookies.get(COOKIE_NAME)
        if token and verify_session(token):
            return await call_next(request)

        # Not authenticated — redirect to login
        return RedirectResponse(url="/login", status_code=302)
