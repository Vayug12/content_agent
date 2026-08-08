"""Content agent API.

Product surface: user topic choose karta hai ya apna script deta hai,
service video banati hai, user download / share karta hai. Bas.
"""

import os
import time
import threading
from typing import Optional
from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, FileResponse
from pydantic import BaseModel
from pathlib import Path
from config import API_KEY, MAX_SCRIPT_CHARS
from utils.logger import log
from utils.jobs import (
    create_job, claim_next_job, get_job, list_jobs, delete_job
)
from utils.storage import delete_video, is_configured as storage_ready
from agents.topic_selector import suggest_topics
from pipeline import run_job

app = FastAPI(
    title="Content Agent API",
    description="Generate short videos from a topic or your own script",
    version="2.0.0"
)

DOCS_DIR = Path(__file__).parent.parent / "docs"
LLM_TXT = Path(__file__).parent.parent / "llm.txt"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/llm.txt", response_class=PlainTextResponse)
def llm_txt():
    """AI agents ke liye quick app reference."""
    if not LLM_TXT.exists():
        raise HTTPException(status_code=404, detail="llm.txt not found")
    return PlainTextResponse(LLM_TXT.read_text(encoding="utf-8"))


@app.get("/docs/{filename}")
def serve_docs(filename: str):
    """Human-readable documentation pages."""
    file_path = DOCS_DIR / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Doc not found")
    return FileResponse(file_path, media_type="text/markdown")


def require_key(x_api_key: Optional[str]):
    """Shared secret. Real per-user auth abhi baaki hai - dekho README."""
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# ==================== WORKER ====================

_worker_started = False


def worker_loop():
    """Queued jobs uthao aur ek-ek karke chalao.

    Ek worker = ek render at a time. Rendering CPU-bound hai, parallel
    chalane se dono slow ho jaate hai. Zyada throughput chahiye toh aur
    worker process chalao (claim_next_job ka note padho pehle).
    """
    log("WORKER", "Worker started")
    while True:
        try:
            job = claim_next_job()
            if job:
                run_job(job)
            else:
                time.sleep(5)
        except Exception as e:
            log("WORKER", f"Loop error: {str(e)}")
            time.sleep(5)


@app.on_event("startup")
def start_worker():
    global _worker_started
    if not _worker_started:
        threading.Thread(target=worker_loop, daemon=True).start()
        _worker_started = True


# ==================== MODELS ====================

class JobRequest(BaseModel):
    user_id: str
    prompt: Optional[str] = ""   # Topic ya idea
    script: Optional[str] = ""   # User ka apna script (optional)


# ==================== ENDPOINTS ====================

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "storage_configured": storage_ready(),
    }


@app.get("/topics/suggestions")
def topic_suggestions(
    count: int = Query(6, ge=1, le=12),
    category: Optional[str] = None,
    x_api_key: Optional[str] = Header(None),
):
    """Picker screen ke liye topic suggestions."""
    require_key(x_api_key)
    return {"topics": suggest_topics(count=count, category=category)}


@app.post("/jobs", status_code=202)
def submit_job(request: JobRequest, x_api_key: Optional[str] = Header(None)):
    """Video generation queue me daalo. Turant job_id milta hai."""
    require_key(x_api_key)

    if not request.prompt and not request.script:
        raise HTTPException(status_code=400, detail="Provide a prompt or a script")
    if request.script and len(request.script) > MAX_SCRIPT_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"Script too long (max {MAX_SCRIPT_CHARS} characters)"
        )
    if not storage_ready():
        raise HTTPException(status_code=503, detail="Storage not configured")

    job = create_job(
        user_id=request.user_id,
        prompt=request.prompt or "",
        script=request.script or "",
    )
    if not job:
        raise HTTPException(status_code=500, detail="Could not create job")
    return job


@app.get("/jobs/{job_id}")
def job_status(job_id: str, user_id: str, x_api_key: Optional[str] = Header(None)):
    """Progress polling - app yahi se stage dikhata hai."""
    require_key(x_api_key)
    job = get_job(job_id, user_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/jobs")
def user_library(
    user_id: str,
    limit: int = Query(50, ge=1, le=100),
    x_api_key: Optional[str] = Header(None),
):
    """User ki banayi hui saari videos."""
    require_key(x_api_key)
    return {"jobs": list_jobs(user_id, limit=limit)}


@app.delete("/jobs/{job_id}")
def remove_job(job_id: str, user_id: str, x_api_key: Optional[str] = Header(None)):
    """Library se video hatao - R2 se file bhi delete hoti hai."""
    require_key(x_api_key)
    job = delete_job(job_id, user_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("video_key"):
        delete_video(job["video_key"])
    return {"success": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "7860")))
