"""SQLite database for job tracking."""

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from config import DATABASE_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id            TEXT PRIMARY KEY,
    youtube_url   TEXT NOT NULL,
    video_id      TEXT,
    status        TEXT DEFAULT 'pending',
    step          TEXT DEFAULT '',
    video_title   TEXT DEFAULT '',
    thumbnail_url TEXT DEFAULT '',
    error         TEXT DEFAULT '',
    created_at    TEXT NOT NULL,
    completed_at  TEXT DEFAULT ''
);
"""


def _connect() -> sqlite3.Connection:
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(_SCHEMA)
    # Migrations for columns added after initial schema
    try:
        conn.execute("ALTER TABLE jobs ADD COLUMN video_duration INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # Column already exists
    conn.commit()
    return conn


_conn: sqlite3.Connection | None = None


def get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = _connect()
    return _conn


def generate_job_id() -> str:
    return uuid.uuid4().hex[:8]


def create_job(youtube_url: str, video_id: str | None = None) -> dict:
    conn = get_conn()
    job_id = generate_job_id()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO jobs (id, youtube_url, video_id, status, created_at) VALUES (?, ?, ?, 'pending', ?)",
        (job_id, youtube_url, video_id or "", now),
    )
    conn.commit()
    return get_job(job_id)


def get_job(job_id: str) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if row is None:
        return None
    return dict(row)


def find_job_by_video_id(video_id: str) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM jobs WHERE video_id = ? ORDER BY created_at DESC LIMIT 1",
        (video_id,),
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def update_job(job_id: str, **fields) -> None:
    conn = get_conn()
    sets = ", ".join(f"{k} = ?" for k in fields)
    vals = list(fields.values()) + [job_id]
    conn.execute(f"UPDATE jobs SET {sets} WHERE id = ?", vals)
    conn.commit()


def list_jobs(limit: int = 50) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]
