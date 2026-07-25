import json
import os
import time
import re
import requests
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL, VAYUG_API_BASE
from agents.auth import get_jwt
from utils.logger import log

client = Groq(api_key=GROQ_API_KEY)


def generate_metadata(script_data: dict, research_data: dict) -> dict:
    log("METADATA", "Generating YouTube metadata...")

    SYSTEM_PROMPT = """You are a YouTube SEO expert. Generate optimized metadata for a YouTube Short.

Return JSON only:
{
  "title": "optimized title (max 60 chars)",
  "description": "SEO optimized description (max 500 chars)",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3"]
}

Rules:
- Title must be catchy and include keywords
- Description must include relevant keywords naturally
- Tags must be relevant and trending
- Use power words that drive clicks"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Generate YouTube metadata for:\n\nTitle: {script_data['title']}\nTopic: {script_data.get('title', '')}\nTags: {', '.join(script_data.get('tags', []))}\nResearch: {json.dumps(research_data.get('facts', [])[:3])}\n\nReturn JSON only."}
        ],
        temperature=0.7,
        max_tokens=600
    )

    try:
        content = response.choices[0].message.content
        cleaned = re.sub(r'```json\s*', '', content)
        cleaned = re.sub(r'```\s*', '', cleaned)
        match = re.search(r'\{[\s\S]*\}', cleaned)
        if match:
            result = json.loads(match.group())
        else:
            result = json.loads(cleaned)
        log("METADATA", f"Title: {result['title']}")
        return result
    except:
        log("METADATA", "Metadata parse failed, using defaults")
        return {
            "title": script_data["title"],
            "description": script_data["title"],
            "tags": script_data.get("tags", []),
            "hashtags": ["#tech", "#shorts"]
        }


def get_presigned_url(jwt: str, filename: str) -> dict:
    log("PUBLISH", "Step 1: Getting presigned URL...")
    resp = requests.get(
        f"{VAYUG_API_BASE}/api/agent/upload/presigned-url",
        params={"filename": filename},
        headers={"Authorization": f"Bearer {jwt}"}
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("success"):
        raise Exception(f"Presigned URL failed: {data}")
    log("PUBLISH", f"Got upload URL, key: {data['key']}")
    return data


def upload_to_r2(upload_url: str, video_path: str) -> None:
    log("PUBLISH", "Step 2: Uploading video to R2...")
    file_size = os.path.getsize(video_path)
    log("PUBLISH", f"File size: {file_size / (1024*1024):.1f} MB")

    with open(video_path, "rb") as f:
        resp = requests.put(
            upload_url,
            data=f,
            headers={"Content-Type": "video/mp4"}
        )
    resp.raise_for_status()
    log("PUBLISH", "Video uploaded to R2 successfully")


def register_video(jwt: str, r2_key: str, metadata: dict) -> dict:
    log("PUBLISH", "Step 3: Registering video on backend...")
    payload = {
        "r2Key": r2_key,
        "videoName": metadata.get("title", "AI Generated Video"),
        "description": metadata.get("description", ""),
        "category": "education",
        "tags": metadata.get("tags", ["ai", "tech", "shorts"])
    }
    resp = requests.post(
        f"{VAYUG_API_BASE}/api/agent/upload/register",
        json=payload,
        headers={"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"}
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("success"):
        raise Exception(f"Register failed: {data}")
    video_id = data["video"]["id"]
    log("PUBLISH", f"Video registered, ID: {video_id}")
    return data


def poll_status(jwt: str, video_id: str, max_wait: int = 300) -> dict:
    log("PUBLISH", "Step 4: Waiting for processing...")
    start = time.time()

    while time.time() - start < max_wait:
        resp = requests.get(
            f"{VAYUG_API_BASE}/api/agent/upload/status/{video_id}",
            headers={"Authorization": f"Bearer {jwt}"}
        )
        resp.raise_for_status()
        data = resp.json()
        status = data["video"]["processingStatus"]
        progress = data["video"].get("processingProgress", 0)

        log("PUBLISH", f"Status: {status} ({progress}%)")

        if status == "completed":
            log("PUBLISH", f"Video URL: {data['video'].get('videoUrl', 'N/A')}")
            return data
        elif status == "failed":
            raise Exception(f"Processing failed: {data['video'].get('error')}")

        time.sleep(10)

    raise Exception("Processing timed out after 5 minutes")


def upload_download_copy(video_path: str) -> dict:
    """
    Upload a DURABLE MP4 copy for gallery download.

    The normal publish path (register + HLS transcode) deletes the source MP4,
    leaving only a streaming playlist that can't be saved to a phone gallery.
    This uploads the same MP4 to a persistent ai_downloads/ location.

    Returns {"url": <public url>, "key": <r2 key>} so the backend can delete the
    object once the user has downloaded it. Returns {} on any failure (download
    is optional; it must never break publishing).
    """
    jwt = get_jwt()
    if not jwt:
        log("DOWNLOAD", "Auth failed - skipping download copy")
        return {}
    if not os.path.exists(video_path):
        log("DOWNLOAD", f"Video not found: {video_path}")
        return {}

    try:
        filename = os.path.basename(video_path)
        resp = requests.get(
            f"{VAYUG_API_BASE}/api/agent/upload/download-url",
            params={"filename": filename},
            headers={"Authorization": f"Bearer {jwt}"}
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            log("DOWNLOAD", f"Download URL request failed: {data}")
            return {}

        with open(video_path, "rb") as f:
            put = requests.put(
                data["uploadUrl"],
                data=f,
                headers={"Content-Type": "video/mp4"}
            )
        put.raise_for_status()

        download_url = data.get("downloadUrl", "")
        download_key = data.get("key", "")
        log("DOWNLOAD", f"Durable MP4 uploaded: {download_url}")
        return {"url": download_url, "key": download_key}
    except Exception as e:
        log("DOWNLOAD", f"Failed to upload download copy: {e}")
        return {}


def publish_to_vayug(video_path: str, metadata: dict) -> dict:
    jwt = get_jwt()
    if not jwt:
        log("PUBLISH", "Authentication failed - skipping publish")
        return {}

    if not os.path.exists(video_path):
        log("PUBLISH", f"Video not found: {video_path}")
        return {}

    try:
        filename = os.path.basename(video_path)

        presigned = get_presigned_url(jwt, filename)
        upload_to_r2(presigned["uploadUrl"], video_path)
        register_result = register_video(jwt, presigned["key"], metadata)
        video_id = register_result["video"]["id"]
        final = poll_status(jwt, video_id)

        log("PUBLISH", "=" * 50)
        log("PUBLISH", "VIDEO PUBLISHED TO VAYUG SUCCESSFULLY!")
        log("PUBLISH", f"Video URL: {final['video'].get('videoUrl', 'N/A')}")
        log("PUBLISH", f"Thumbnail: {final['video'].get('thumbnailUrl', 'N/A')}")
        log("PUBLISH", "=" * 50)

        return final

    except Exception as e:
        log("PUBLISH", f"Publish failed: {str(e)}")
        return {}
