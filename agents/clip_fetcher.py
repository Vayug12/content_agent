import os
import re
import time
import subprocess
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import yt_dlp
from config import (
    PEXELS_API_KEY, OUTPUT_DIR,
    YOUTUBE_MAX_FILESIZE, YOUTUBE_SEARCH_COUNT,
    YOUTUBE_MIN_DURATION, YOUTUBE_MAX_DURATION,
    YOUTUBE_MAX_HEIGHT
)
from utils.logger import log


def get_session():
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


# ==================== YOUTUBE FUNCTIONS ====================

def search_youtube(query: str, max_results: int = YOUTUBE_SEARCH_COUNT) -> list:
    """YouTube pe video search karo - any video, not just stock footage"""
    log("CLIPS", f"YouTube search: '{query}'")

    search_query = f"{query}"
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(f"ytsearch{max_results}:{search_query}", download=False)

        entries = result.get('entries', [])
        filtered = []

        for r in entries:
            duration = r.get('duration', 0) or 0
            if duration and YOUTUBE_MIN_DURATION <= duration <= YOUTUBE_MAX_DURATION:
                filtered.append({
                    'url': f"https://www.youtube.com/watch?v={r['id']}",
                    'title': r.get('title', 'Unknown'),
                    'duration': duration,
                    'channel': r.get('channel', 'Unknown') or r.get('uploader', 'Unknown'),
                    'view_count': r.get('view_count', 0) or 0,
                })

        log("CLIPS", f"YouTube: {len(filtered)} videos found")
        return filtered

    except Exception as e:
        log("CLIPS", f"YouTube search error: {str(e)}")
        return []


def download_youtube_clip(url: str, filename: str) -> str:
    """YouTube video download karo - MUTED (sirf visual)"""
    output_path = os.path.join(OUTPUT_DIR, filename)

    ydl_opts = {
        'format': f'bestvideo[height<={YOUTUBE_MAX_HEIGHT}][ext=mp4]/bestvideo[height<={YOUTUBE_MAX_HEIGHT}]/best',
        'outtmpl': output_path,
        'merge_output_format': 'mp4',
        'max_filesize': YOUTUBE_MAX_FILESIZE,
        'no_warnings': True,
        'quiet': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        if os.path.exists(output_path):
            mute_video(output_path)
            log("CLIPS", f"YouTube downloaded + muted: {filename}")
            return output_path

    except Exception as e:
        log("CLIPS", f"YouTube download error: {str(e)}")
        if os.path.exists(output_path):
            os.remove(output_path)

    return ""


def mute_video(video_path: str):
    """Video se audio remove karo using FFmpeg - guaranteed mute"""
    temp_path = video_path + ".temp.mp4"

    try:
        cmd = [
            "ffmpeg", "-i", video_path,
            "-an",
            "-c:v", "copy",
            "-y",
            temp_path
        ]
        subprocess.run(cmd, capture_output=True, timeout=60)

        if os.path.exists(temp_path):
            os.replace(temp_path, video_path)
    except Exception as e:
        log("CLIPS", f"Mute error: {str(e)}")
        if os.path.exists(temp_path):
            os.remove(temp_path)


def trim_to_short_clip(video_path: str, target_duration: float) -> str:
    """Video ko scene duration ke according trim karo (middle section - best action)"""
    from moviepy import VideoFileClip

    try:
        clip = VideoFileClip(video_path)
        total_duration = clip.duration

        # Agar clip already chota hai toh as-is use karo
        if total_duration <= target_duration:
            clip = clip.without_audio()
            clip.close()
            return video_path

        # Middle section se trim karo (usually best action hota hai)
        start_time = (total_duration - target_duration) / 2
        end_time = start_time + target_duration

        trimmed = clip.subclipped(start_time, end_time)
        trimmed = trimmed.without_audio()

        trimmed_path = video_path.replace(".mp4", "_trimmed.mp4")
        trimmed.write_videofile(
            trimmed_path,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            logger=None
        )

        clip.close()
        trimmed.close()

        os.remove(video_path)
        log("CLIPS", f"Trimmed: {total_duration:.1f}s -> {target_duration:.1f}s")
        return trimmed_path

    except Exception as e:
        log("CLIPS", f"Trim error: {str(e)}")
        return video_path


# ==================== PEXELS FUNCTIONS ====================

def search_pexels(query: str, count: int = 2) -> list:
    """Pexels API se stock footage search karo (fallback)"""
    if not PEXELS_API_KEY:
        log("CLIPS", "Pexels API key not set, skipping Pexels")
        return []

    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": count, "orientation": "portrait"}

    session = get_session()
    try:
        response = session.get(
            "https://api.pexels.com/videos/search",
            headers=headers,
            params=params,
            timeout=30
        )

        if response.status_code != 200:
            log("CLIPS", f"Pexels search failed for: {query}")
            return []

        data = response.json()
        clips = []

        for video in data.get("videos", []):
            best_file = max(video.get("video_files", []),
                            key=lambda f: f.get("height", 0))
            if best_file:
                clips.append({
                    "url": best_file["link"],
                    "width": best_file.get("width", 0),
                    "height": best_file.get("height", 0),
                    "duration": video.get("duration", 0)
                })

        log("CLIPS", f"Pexels: {len(clips)} clips found")
        return clips

    except Exception as e:
        log("CLIPS", f"Pexels search error: {str(e)}")
        return []


def download_clip(url: str, filename: str, max_retries: int = 3) -> str:
    """Generic video download function"""
    output_path = os.path.join(OUTPUT_DIR, filename)

    for attempt in range(max_retries):
        try:
            session = get_session()
            response = session.get(url, stream=True, timeout=60)

            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                log("CLIPS", f"Downloaded: {filename}")
                return output_path

        except (requests.exceptions.ChunkedEncodingError,
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:
            log("CLIPS", f"Download error (attempt {attempt + 1}/{max_retries}): {filename}")
            if os.path.exists(output_path):
                os.remove(output_path)
            time.sleep(2)

    log("CLIPS", f"Failed to download after {max_retries} attempts: {filename}")
    return ""


# ==================== MAIN FETCH FUNCTION ====================

def fetch_all_clips(scenes: list) -> list:
    """Multi-source clip fetcher - YouTube first, Pexels fallback"""
    log("CLIPS", "Fetching clips from YouTube + Pexels...")
    downloaded = []

    for i, scene in enumerate(scenes):
        query = scene["clip_search_query"]
        scene_duration = scene["duration"]
        log("CLIPS", f"Scene {i+1}: searching '{query}'")

        clip_path = ""

        # SOURCE 1: YouTube (primary - any video)
        yt_clips = search_youtube(query, max_results=3)
        if yt_clips:
            # Best clip select karo (most views)
            best = max(yt_clips, key=lambda x: x['view_count'])
            filename = f"clip_{i+1}.mp4"
            path = download_youtube_clip(best['url'], filename)

            if path:
                # Trim to scene duration (dynamic - 4-8 seconds)
                clip_path = trim_to_short_clip(path, target_duration=scene_duration)
                log("CLIPS", f"Scene {i+1}: YouTube clip used ({best['title'][:40]})")

        # SOURCE 2: Pexels (fallback - stock footage)
        if not clip_path:
            pexels_clips = search_pexels(query, count=1)
            if pexels_clips:
                filename = f"clip_{i+1}.mp4"
                clip_path = download_clip(pexels_clips[0]['url'], filename)
                log("CLIPS", f"Scene {i+1}: Pexels clip used")

        if not clip_path:
            log("CLIPS", f"Scene {i+1}: No clips found")

        downloaded.append({
            "scene_number": scene["scene_number"],
            "path": clip_path,
            "duration": scene["duration"]
        })

        # Rate limiting - YouTube ke liye
        time.sleep(1)

    return downloaded
