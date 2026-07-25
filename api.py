import os
import json
import requests
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from config import OUTPUT_DIR
from utils.logger import log
from agents.topic_selector import select_topic
from agents.research_agent import research_topic
from agents.script_writer import write_script
from agents.review_agent import review_script, review_assets
from agents.clip_fetcher import fetch_all_clips
from agents.voice_generator import generate_all_voices
from agents.video_editor import edit_video
from agents.publishing_agent import generate_metadata, publish_to_vayug, upload_download_copy
from agents.analytics_agent import analyze_performance
from agents.prompt_enhancer import enhance_prompt
from utils.memory import add_to_memory, get_memory_stats, add_pipeline_run, get_all_topics

app = FastAPI(
    title="VayugAI API",
    description="REST API wrapper for VayugAI content generation agents",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"status": "healthy", "message": "Vayu AI Agent is running"}


class TopicRequest(BaseModel):
    category: Optional[str] = None


class ResearchRequest(BaseModel):
    topic: str
    category: Optional[str] = "Unknown"
    keywords: Optional[List[str]] = []


class ScriptRequest(BaseModel):
    topic: str
    category: Optional[str] = "Unknown"
    keywords: Optional[List[str]] = []
    audience: Optional[str] = "Tech enthusiasts"


class ReviewRequest(BaseModel):
    script_data: dict
    research_data: dict


class ClipsRequest(BaseModel):
    scenes: list


class VoiceRequest(BaseModel):
    scenes: list


class EditRequest(BaseModel):
    scenes: list
    clips: list
    voices: list


class MetadataRequest(BaseModel):
    script_data: dict
    research_data: dict


class PublishRequest(BaseModel):
    video_path: str
    metadata: dict


class GenerateRequest(BaseModel):
    prompt: str
    category: Optional[str] = None
    audience: Optional[str] = None
    skip_publish: Optional[bool] = False
    # Set by the Vayug backend so the agent can report completion back to it.
    job_id: Optional[str] = None
    callback_url: Optional[str] = None
    callback_secret: Optional[str] = None


class PipelineRequest(BaseModel):
    topic: Optional[str] = None
    category: Optional[str] = None
    keywords: Optional[List[str]] = []
    audience: Optional[str] = "Tech enthusiasts"
    skip_publish: Optional[bool] = False


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "VayugAI API"}


@app.get("/stats")
def get_stats():
    stats = get_memory_stats()
    return {
        "total_runs": stats["total_runs"],
        "topics_used": stats["topics_used"]
    }


@app.get("/topics")
def get_topics(limit: int = 20):
    topics = get_all_topics(limit=limit)
    return {"topics": topics}


@app.post("/topic")
def create_topic(request: TopicRequest = None):
    try:
        topic_data = select_topic()
        add_to_memory(topic_data)
        return {"success": True, "data": topic_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/research")
def create_research(request: ResearchRequest):
    try:
        topic_data = {
            "topic": request.topic,
            "category": request.category,
            "keywords": request.keywords
        }
        research_data = research_topic(topic_data)
        return {"success": True, "data": research_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/script")
def create_script(request: ScriptRequest):
    try:
        topic_data = {
            "topic": request.topic,
            "category": request.category,
            "keywords": request.keywords,
            "audience": request.audience
        }
        script_data = write_script(topic_data)
        return {"success": True, "data": script_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/review")
def create_review(request: ReviewRequest):
    try:
        review_result = review_script(request.script_data, request.research_data)
        return {"success": True, "data": review_result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/clips")
def create_clips(request: ClipsRequest):
    try:
        clips = fetch_all_clips(request.scenes)
        return {"success": True, "data": clips}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/voice")
def create_voice(request: VoiceRequest):
    try:
        voices = generate_all_voices(request.scenes)
        return {"success": True, "data": voices}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/edit")
def create_edit(request: EditRequest):
    try:
        final_video = edit_video(request.scenes, request.clips, request.voices)
        return {"success": True, "data": {"video_path": final_video}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/metadata")
def create_metadata(request: MetadataRequest):
    try:
        metadata = generate_metadata(request.script_data, request.research_data)
        return {"success": True, "data": metadata}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/publish")
def create_publish(request: PublishRequest):
    try:
        result = publish_to_vayug(request.video_path, request.metadata)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analytics")
def create_analytics():
    try:
        result = analyze_performance()
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def run_full_pipeline_sync(request: PipelineRequest):
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        if request.topic:
            topic_data = {
                "topic": request.topic,
                "category": request.category or "Unknown",
                "keywords": request.keywords or [],
                "audience": request.audience or "Tech enthusiasts"
            }
        else:
            topic_data = select_topic()
            add_to_memory(topic_data)

        research_data = research_topic(topic_data)

        topic_data["research"] = research_data
        script_data = write_script(topic_data)

        review_result = review_script(script_data, research_data)

        if not review_result["approved"] and review_result["score"] < 5:
            script_data = write_script(topic_data)
            review_result = review_script(script_data, research_data)

        scenes = script_data["scenes"]
        clips = fetch_all_clips(scenes)
        voices = generate_all_voices(scenes)

        asset_review = review_assets(clips, voices, scenes)

        final_video = edit_video(scenes, clips, voices)

        metadata = {}
        publish_result = {}

        if final_video:
            metadata = generate_metadata(script_data, research_data)

            if not request.skip_publish:
                publish_result = publish_to_vayug(final_video, metadata)

            # Sirf data save karo
            add_pipeline_run(
                topic=topic_data["topic"],
                title=metadata.get("title", ""),
                tags=metadata.get("tags", []),
                video_url=publish_result.get("video", {}).get("videoUrl", ""),
                status="success"
            )

            # Video DELETE karo
            if os.path.exists(final_video):
                os.remove(final_video)
        else:
            add_pipeline_run(
                topic=topic_data["topic"],
                title="",
                tags=[],
                video_url="",
                status="failed"
            )

        return {
            "success": True,
            "data": {
                "topic": topic_data,
                "script": script_data,
                "review": review_result,
                "asset_review": asset_review,
                "video_url": publish_result.get("video", {}).get("videoUrl", ""),
                "metadata": metadata,
                "publish": publish_result
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/pipeline/run")
def run_pipeline(request: PipelineRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_full_pipeline_sync, request)
    return {"success": True, "message": "Pipeline started in background"}


@app.post("/pipeline/run-sync")
def run_pipeline_sync(request: PipelineRequest):
    result = run_full_pipeline_sync(request)
    if result["success"]:
        return result
    else:
        raise HTTPException(status_code=500, detail=result["error"])


def notify_backend(callback_url: str, callback_secret: str, payload: dict):
    """
    Report generation result back to the Vayug backend webhook.
    No-op if no callback_url was provided (e.g. direct /generate-sync calls).
    Never raises — a failed notification must not crash the pipeline task.
    """
    if not callback_url:
        return
    try:
        headers = {"Content-Type": "application/json"}
        if callback_secret:
            headers["x-vayug-webhook-secret"] = callback_secret
        resp = requests.post(callback_url, json=payload, headers=headers, timeout=15)
        log("CALLBACK", f"Notified backend [{resp.status_code}] status={payload.get('status')}")
    except Exception as e:
        log("CALLBACK", f"Failed to notify backend at {callback_url}: {e}")


def run_generate_pipeline_sync(request: GenerateRequest):
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # Step 0: Enhance user prompt into full topic_data
        topic_data = enhance_prompt(
            user_prompt=request.prompt,
            category=request.category,
            audience=request.audience
        )
        add_to_memory(topic_data)

        # Step 1: Research Agent - Research the topic
        research_data = research_topic(topic_data)

        # Step 2: Content Agent - Write script
        topic_data["research"] = research_data
        script_data = write_script(topic_data)

        # Step 3: Review Agent - Review the script
        review_result = review_script(script_data, research_data)

        if not review_result["approved"] and review_result["score"] < 5:
            script_data = write_script(topic_data)
            review_result = review_script(script_data, research_data)

        scenes = script_data["scenes"]

        # Step 4: Content Agent - Fetch clips and generate voice
        clips = fetch_all_clips(scenes)
        voices = generate_all_voices(scenes)

        # Step 4.5: Review Agent - Check assets
        asset_review = review_assets(clips, voices, scenes)

        # Step 5: Content Agent - Edit video
        final_video = edit_video(scenes, clips, voices)

        metadata = {}
        publish_result = {}
        download_url = ""
        download_key = ""

        if final_video:
            metadata = generate_metadata(script_data, research_data)

            if not request.skip_publish:
                publish_result = publish_to_vayug(final_video, metadata)

            # Upload a durable MP4 copy for gallery download BEFORE deleting the
            # local file (the HLS publish path leaves no downloadable MP4).
            download_copy = upload_download_copy(final_video)
            download_url = download_copy.get("url", "")
            download_key = download_copy.get("key", "")

            add_pipeline_run(
                topic=topic_data["topic"],
                title=metadata.get("title", ""),
                tags=metadata.get("tags", []),
                video_url=publish_result.get("video", {}).get("videoUrl", ""),
                status="success"
            )

            if os.path.exists(final_video):
                os.remove(final_video)
        else:
            add_pipeline_run(
                topic=topic_data["topic"],
                title="",
                tags=[],
                video_url="",
                status="failed"
            )

        video_url = publish_result.get("video", {}).get("videoUrl", "")
        video_id = publish_result.get("video", {}).get("id")

        # Report result back to the Vayug backend (if it asked for a callback).
        if video_url:
            notify_backend(request.callback_url, request.callback_secret, {
                "status": "completed",
                "video_url": video_url,
                "download_url": download_url,
                "download_key": download_key,
                "video_id": video_id,
                "metadata": metadata,
            })
        else:
            # Pipeline ran but produced no usable video URL (edit or publish failed).
            notify_backend(request.callback_url, request.callback_secret, {
                "status": "failed",
                "error": "Video was generated but could not be published (no video URL).",
            })

        return {
            "success": True,
            "data": {
                "topic": topic_data,
                "script": script_data,
                "review": review_result,
                "asset_review": asset_review,
                "video_url": video_url,
                "metadata": metadata,
                "publish": publish_result
            }
        }
    except Exception as e:
        # Report the failure back so the backend can mark the job failed
        # instead of leaving it stuck in 'processing' forever.
        notify_backend(request.callback_url, request.callback_secret, {
            "status": "failed",
            "error": str(e),
        })
        return {"success": False, "error": str(e)}


@app.post("/generate")
def generate_from_prompt(request: GenerateRequest, background_tasks: BackgroundTasks):
    """Generate a video from a user prompt. Enhances the prompt and runs the full pipeline."""
    background_tasks.add_task(run_generate_pipeline_sync, request)
    return {"success": True, "message": "Video generation started from your prompt"}


@app.post("/generate-sync")
def generate_from_prompt_sync(request: GenerateRequest):
    """Generate a video from a user prompt (synchronous)."""
    result = run_generate_pipeline_sync(request)
    if result["success"]:
        return result
    else:
        raise HTTPException(status_code=500, detail=result["error"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
