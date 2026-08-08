"""Video generation pipeline.

Do entry points hai:
  1. prompt  -> enhance -> research -> write script
  2. script  -> parse into scenes (user ke apne words, verbatim)

Dono ke baad flow same hai: clips -> voice -> render -> R2 upload.
"""

import os
import shutil
from config import OUTPUT_DIR
from utils.logger import log
from utils.jobs import set_stage, complete_job, fail_job
from utils.storage import upload_video, is_configured as storage_ready
from agents.prompt_enhancer import enhance_prompt
from agents.research_agent import research_topic
from agents.script_writer import write_script
from agents.script_parser import parse_script
from agents.clip_fetcher import fetch_all_clips
from agents.voice_generator import generate_all_voices
from agents.video_editor import edit_video


def build_script(job: dict) -> dict:
    """Job ke type ke hisaab se script banao ya parse karo."""
    if job.get("script"):
        log("PIPELINE", "User-supplied script - skipping research/writer")
        return parse_script(job["script"], title=job.get("prompt", ""))

    topic_data = enhance_prompt(user_prompt=job.get("prompt", ""))
    topic_data["research"] = research_topic(topic_data)
    return write_script(topic_data)


def run_job(job: dict) -> dict:
    """Ek job end-to-end chalao. Kabhi raise nahi karta - job row me status likhta hai."""
    job_id = job["id"]
    out_dir = os.path.join(OUTPUT_DIR, job_id)

    try:
        if not storage_ready():
            raise RuntimeError("R2 storage is not configured - video would be lost")

        # Har job apni directory me - do users kabhi ek dusre ki files overwrite na kare
        os.makedirs(out_dir, exist_ok=True)

        set_stage(job_id, "scripting")
        script_data = build_script(job)
        scenes = script_data["scenes"]
        log("PIPELINE", f"{len(scenes)} scenes ready")

        set_stage(job_id, "clips")
        clips = fetch_all_clips(scenes, out_dir)

        set_stage(job_id, "voice")
        voices = generate_all_voices(scenes, out_dir)

        set_stage(job_id, "rendering")
        final_video = edit_video(scenes, clips, voices, out_dir)
        if not final_video or not os.path.exists(final_video):
            raise RuntimeError("Rendering produced no video")

        set_stage(job_id, "uploading")
        key = f"videos/{job['user_id']}/{job_id}.mp4"
        uploaded = upload_video(final_video, key)
        if not uploaded:
            raise RuntimeError("Upload to R2 failed")

        title = script_data.get("title", "Untitled")
        complete_job(job_id, title, uploaded["url"], uploaded["key"])
        log("PIPELINE", f"Job {job_id} done: {title}")
        return {"success": True, "video_url": uploaded["url"], "title": title}

    except Exception as e:
        log("PIPELINE", f"Job {job_id} failed: {str(e)}")
        fail_job(job_id, str(e))
        return {"success": False, "error": str(e)}

    finally:
        # Disk ephemeral hai aur chhoti bhi - job ka kachra hamesha saaf karo
        shutil.rmtree(out_dir, ignore_errors=True)
