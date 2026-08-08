"""Video job store — SQLite.

Job row hi single source of truth hai — app isi ko poll karke progress dikhata hai.
SQLite sirf ek file hai, zero setup, data server restart pe safe rehta hai.
"""

import uuid
import sqlite3
from pathlib import Path
from config import DB_PATH
from utils.logger import log

STAGES = ["queued", "scripting", "clips", "voice", "rendering", "uploading", "done"]


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = _conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS video_jobs (
            id          TEXT PRIMARY KEY,
            user_id     TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'queued',
            stage       TEXT NOT NULL DEFAULT 'queued',
            prompt      TEXT DEFAULT '',
            script      TEXT DEFAULT '',
            title       TEXT DEFAULT '',
            video_url   TEXT DEFAULT '',
            video_key   TEXT DEFAULT '',
            error       TEXT DEFAULT '',
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_user ON video_jobs(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON video_jobs(status)")
    conn.commit()
    conn.close()


_init_db()


def create_job(user_id: str, prompt: str = "", script: str = "") -> dict:
    """Naya job queue me daalo. Worker isko uthayega."""
    job_id = str(uuid.uuid4())
    try:
        conn = _conn()
        conn.execute(
            "INSERT INTO video_jobs (id, user_id, status, stage, prompt, script) VALUES (?, ?, 'queued', 'queued', ?, ?)",
            (job_id, user_id, prompt, script),
        )
        conn.commit()
        conn.close()
        log("JOBS", f"Created job {job_id} for user {user_id}")
        return {"id": job_id, "status": "queued", "stage": "queued"}
    except Exception as e:
        log("JOBS", f"Error creating job: {str(e)}")
        return {}


def claim_next_job() -> dict:
    """Sabse purana queued job uthao aur processing mark karo."""
    try:
        conn = _conn()
        row = conn.execute(
            "SELECT * FROM video_jobs WHERE status='queued' ORDER BY created_at LIMIT 1"
        ).fetchone()
        if not row:
            conn.close()
            return {}
        job = dict(row)
        conn.execute(
            "UPDATE video_jobs SET status='processing', stage='scripting' WHERE id=? AND status='queued'",
            (job["id"],),
        )
        conn.commit()
        conn.close()
        log("JOBS", f"Claimed job {job['id']}")
        return job
    except Exception as e:
        log("JOBS", f"Error claiming job: {str(e)}")
        return {}


def set_stage(job_id: str, stage: str):
    """Progress update — app polling se yahi dikhata hai."""
    try:
        conn = _conn()
        conn.execute("UPDATE video_jobs SET stage=? WHERE id=?", (stage, job_id))
        conn.commit()
        conn.close()
        log("JOBS", f"Job {job_id}: {stage}")
    except Exception as e:
        log("JOBS", f"Error setting stage: {str(e)}")


def complete_job(job_id: str, title: str, video_url: str, video_key: str):
    try:
        conn = _conn()
        conn.execute(
            "UPDATE video_jobs SET status='completed', stage='done', title=?, video_url=?, video_key=? WHERE id=?",
            (title, video_url, video_key, job_id),
        )
        conn.commit()
        conn.close()
        log("JOBS", f"Job {job_id} completed")
    except Exception as e:
        log("JOBS", f"Error completing job: {str(e)}")


def fail_job(job_id: str, error: str):
    try:
        conn = _conn()
        conn.execute(
            "UPDATE video_jobs SET status='failed', error=? WHERE id=?",
            (error[:500], job_id),
        )
        conn.commit()
        conn.close()
        log("JOBS", f"Job {job_id} failed: {error}")
    except Exception as e:
        log("JOBS", f"Error failing job: {str(e)}")


def get_job(job_id: str, user_id: str) -> dict:
    """user_id filter zaroori hai — warna koi bhi dusre ka job padh lega."""
    try:
        conn = _conn()
        row = conn.execute(
            "SELECT * FROM video_jobs WHERE id=? AND user_id=? LIMIT 1",
            (job_id, user_id),
        ).fetchone()
        conn.close()
        return dict(row) if row else {}
    except Exception as e:
        log("JOBS", f"Error fetching job: {str(e)}")
        return {}


def list_jobs(user_id: str, limit: int = 50) -> list:
    """User ki library."""
    try:
        conn = _conn()
        rows = conn.execute(
            "SELECT id,status,stage,title,video_url,created_at FROM video_jobs WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        log("JOBS", f"Error listing jobs: {str(e)}")
        return []


def delete_job(job_id: str, user_id: str) -> dict:
    """Job row hatao aur R2 key wapas do taaki file bhi delete ho sake."""
    job = get_job(job_id, user_id)
    if not job:
        return {}
    try:
        conn = _conn()
        conn.execute("DELETE FROM video_jobs WHERE id=? AND user_id=?", (job_id, user_id))
        conn.commit()
        conn.close()
        log("JOBS", f"Deleted job {job_id}")
        return job
    except Exception as e:
        log("JOBS", f"Error deleting job: {str(e)}")
        return {}
