import os
import re
import json
import time
from urllib.parse import urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config import (
    PEXELS_API_KEY, PIXABAY_API_KEY,
    CLIP_MAX_FILESIZE, CLIP_SEARCH_COUNT, CLIP_MIN_HEIGHT
)
from utils.logger import log


# Wikimedia descriptive User-Agent maangta hai, warna 403 deta hai
USER_AGENT = "creatoragent/1.0 (automated content pipeline)"

VIDEO_EXTENSIONS = (".mp4", ".webm", ".ogv", ".mov", ".m4v")


class ClipTooLarge(Exception):
    """Clip file size cap se bada hai - retry karne ka fayda nahi"""


def get_session():
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def pick_best_file(files: list) -> dict:
    """Sabse chhota file jo CLIP_MIN_HEIGHT se bada ho - warna jo sabse bada mile.

    Purana code hamesha max height leta tha, jisse 4K files download hoti thi
    aur size cap cross ho jata tha. Ye version quality/size balance karta hai.
    """
    usable = [f for f in files if f.get("height", 0) >= CLIP_MIN_HEIGHT]
    if usable:
        return min(usable, key=lambda f: f["height"])
    if files:
        return max(files, key=lambda f: f.get("height", 0))
    return {}


def strip_html(value: str) -> str:
    """Wikimedia ke extmetadata fields me HTML hota hai - plain text nikalo"""
    return re.sub(r"<[^>]+>", "", value or "").strip() or "Unknown"


# ==================== SOURCE 1: PEXELS ====================

def search_pexels(query: str, count: int = CLIP_SEARCH_COUNT) -> list:
    """Pexels API se stock footage search karo (primary source)"""
    if not PEXELS_API_KEY:
        log("CLIPS", "Pexels API key not set, skipping Pexels")
        return []

    session = get_session()

    def request(params: dict) -> list:
        response = session.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": PEXELS_API_KEY},
            params=params,
            timeout=30
        )
        if response.status_code != 200:
            log("CLIPS", f"Pexels search failed ({response.status_code}) for: {query}")
            return []

        clips = []
        for video in response.json().get("videos", []):
            best = pick_best_file([
                {
                    "url": f["link"],
                    "width": f.get("width") or 0,
                    "height": f.get("height") or 0,
                }
                for f in video.get("video_files", []) if f.get("link")
            ])
            if best:
                clips.append({
                    **best,
                    "duration": video.get("duration", 0),
                    "source": "Pexels",
                    "credit": (video.get("user") or {}).get("name", "Unknown"),
                    "license": "Pexels License",
                    "page": video.get("url", ""),
                })
        return clips

    try:
        base = {"query": query, "per_page": count}
        # Output portrait hai, toh pehle portrait try karo
        clips = request({**base, "orientation": "portrait"})
        # Portrait me kuch na mile toh landscape bhi chalega (editor center-crop karta hai)
        if not clips:
            clips = request(base)

        log("CLIPS", f"Pexels: {len(clips)} clips found")
        return clips

    except Exception as e:
        log("CLIPS", f"Pexels search error: {str(e)}")
        return []


# ==================== SOURCE 2: PIXABAY ====================

def search_pixabay(query: str, count: int = CLIP_SEARCH_COUNT) -> list:
    """Pixabay API se stock footage search karo (fallback)"""
    if not PIXABAY_API_KEY:
        log("CLIPS", "Pixabay API key not set, skipping Pixabay")
        return []

    session = get_session()
    try:
        response = session.get(
            "https://pixabay.com/api/videos/",
            params={
                "key": PIXABAY_API_KEY,
                "q": query,
                "per_page": max(count, 3),  # Pixabay ka minimum 3 hai
                "video_type": "film",
                "safesearch": "true",
            },
            timeout=30
        )

        if response.status_code != 200:
            log("CLIPS", f"Pixabay search failed ({response.status_code}) for: {query}")
            return []

        clips = []
        for hit in response.json().get("hits", [])[:count]:
            best = pick_best_file([
                {
                    "url": v["url"],
                    "width": v.get("width") or 0,
                    "height": v.get("height") or 0,
                }
                for v in (hit.get("videos") or {}).values() if v.get("url")
            ])
            if best:
                clips.append({
                    **best,
                    "duration": hit.get("duration", 0),
                    "source": "Pixabay",
                    "credit": hit.get("user", "Unknown"),
                    "license": "Pixabay Content License",
                    "page": hit.get("pageURL", ""),
                })

        log("CLIPS", f"Pixabay: {len(clips)} clips found")
        return clips

    except Exception as e:
        log("CLIPS", f"Pixabay search error: {str(e)}")
        return []


# ==================== SOURCE 3: WIKIMEDIA COMMONS ====================

def search_wikimedia(query: str, count: int = CLIP_SEARCH_COUNT) -> list:
    """Wikimedia Commons se CC-licensed video - koi API key nahi chahiye.

    Stock libraries me jo nahi milta (real events, places, science footage)
    wo yahan mil jata hai. Quality mixed hoti hai, isliye last fallback hai.
    """
    session = get_session()
    try:
        response = session.get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrsearch": f"filetype:video {query}",
                "gsrnamespace": 6,  # File: namespace
                "gsrlimit": count,
                "prop": "imageinfo",
                "iiprop": "url|size|mime|extmetadata",
            },
            timeout=30
        )

        if response.status_code != 200:
            log("CLIPS", f"Wikimedia search failed ({response.status_code}) for: {query}")
            return []

        pages = (response.json().get("query") or {}).get("pages", {})
        clips = []

        for page in pages.values():
            info = (page.get("imageinfo") or [{}])[0]
            url = info.get("url", "")
            if not url:
                continue

            # Commons pe files bahut badi ho sakti hai - download se pehle hi skip karo
            if info.get("size", 0) > CLIP_MAX_FILESIZE:
                continue

            meta = info.get("extmetadata") or {}
            clips.append({
                "url": url,
                "width": info.get("width", 0),
                "height": info.get("height", 0),
                "duration": info.get("duration", 0) or 0,
                "source": "Wikimedia Commons",
                "credit": strip_html((meta.get("Artist") or {}).get("value", "")),
                "license": strip_html((meta.get("LicenseShortName") or {}).get("value", "")),
                "page": page.get("title", ""),
            })

        log("CLIPS", f"Wikimedia: {len(clips)} clips found")
        return clips

    except Exception as e:
        log("CLIPS", f"Wikimedia search error: {str(e)}")
        return []


# ==================== DOWNLOAD ====================

def download_clip(url: str, name: str, out_dir: str, max_retries: int = 3) -> str:
    """Generic video download - size cap ke saath, extension URL se leta hai"""
    ext = os.path.splitext(urlparse(url).path)[1].lower()
    if ext not in VIDEO_EXTENSIONS:
        ext = ".mp4"

    output_path = os.path.join(out_dir, f"{name}{ext}")

    for attempt in range(max_retries):
        written = 0
        try:
            session = get_session()
            with session.get(url, stream=True, timeout=60) as response:
                if response.status_code != 200:
                    log("CLIPS", f"Download failed ({response.status_code}): {name}")
                    return ""

                with open(output_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        written += len(chunk)
                        if written > CLIP_MAX_FILESIZE:
                            raise ClipTooLarge(
                                f"{written // (1024 * 1024)}MB > "
                                f"{CLIP_MAX_FILESIZE // (1024 * 1024)}MB cap"
                            )

            log("CLIPS", f"Downloaded: {name}{ext} ({written // 1024}KB)")
            return output_path

        except ClipTooLarge as e:
            # Size cap har attempt me same rahega - retry mat karo
            log("CLIPS", f"Skipped (too large): {name} - {str(e)}")
            if os.path.exists(output_path):
                os.remove(output_path)
            return ""

        except (requests.exceptions.ChunkedEncodingError,
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:
            log("CLIPS", f"Download error (attempt {attempt + 1}/{max_retries}): {name} - {str(e)}")
            if os.path.exists(output_path):
                os.remove(output_path)
            time.sleep(2)

    log("CLIPS", f"Failed to download after {max_retries} attempts: {name}")
    return ""


# ==================== MAIN FETCH FUNCTION ====================

# Priority order - pehla source jo clip de deta hai wahi use hota hai
SOURCES = [
    ("Pexels", search_pexels),
    ("Pixabay", search_pixabay),
    ("Wikimedia Commons", search_wikimedia),
]


def save_attributions(entries: list, out_dir: str):
    """CC-licensed clips ke liye attribution file - Wikimedia ke liye zaroori hai"""
    if not entries:
        return

    path = os.path.join(out_dir, "attributions.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
        log("CLIPS", f"Attributions saved: {len(entries)} clips")
    except Exception as e:
        log("CLIPS", f"Attribution save error: {str(e)}")


def fetch_all_clips(scenes: list, out_dir: str) -> list:
    """Multi-source clip fetcher - Pexels primary, Pixabay + Wikimedia fallback"""
    log("CLIPS", "Fetching clips from Pexels + Pixabay + Wikimedia Commons...")
    downloaded = []
    attributions = []

    for i, scene in enumerate(scenes):
        query = scene["clip_search_query"]
        log("CLIPS", f"Scene {i+1}: searching '{query}'")

        clip_path = ""

        for source_name, search_fn in SOURCES:
            if clip_path:
                break

            # Ek source ke saare candidates try karo, phir agle source pe jao
            for candidate in search_fn(query):
                path = download_clip(candidate["url"], f"clip_{i+1}", out_dir)
                if path:
                    clip_path = path
                    log("CLIPS", f"Scene {i+1}: {source_name} clip used "
                                 f"({candidate['credit']})")
                    attributions.append({
                        "scene_number": scene["scene_number"],
                        "query": query,
                        "source": candidate["source"],
                        "credit": candidate["credit"],
                        "license": candidate.get("license", ""),
                        "page": candidate.get("page", ""),
                    })
                    break

        if not clip_path:
            log("CLIPS", f"Scene {i+1}: No clips found for '{query}'")

        downloaded.append({
            "scene_number": scene["scene_number"],
            "path": clip_path,
            "duration": scene["duration"]
        })

        # Rate limiting - free tier APIs ke liye
        time.sleep(1)

    save_attributions(attributions, out_dir)
    return downloaded
