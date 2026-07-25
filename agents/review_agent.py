import os
import json
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL, OUTPUT_DIR
from utils.logger import log

client = Groq(api_key=GROQ_API_KEY)


def check_audio_files(scenes: list, voices: list) -> dict:
    issues = []
    voice_map = {v["scene_number"]: v["path"] for v in voices}

    for scene in scenes:
        num = scene["scene_number"]
        voice_path = voice_map.get(num, "")

        if not voice_path:
            issues.append(f"Scene {num}: no voice file path")
        elif not os.path.exists(voice_path):
            issues.append(f"Scene {num}: voice file missing - {voice_path}")
        elif os.path.getsize(voice_path) < 1000:
            issues.append(f"Scene {num}: voice file too small (corrupt?)")

    return {"passed": len(issues) == 0, "issues": issues}


def check_clips(scenes: list, clips: list) -> dict:
    issues = []
    clip_map = {c["scene_number"]: c for c in clips}

    for scene in scenes:
        num = scene["scene_number"]
        clip_data = clip_map.get(num, {})
        clip_path = clip_data.get("path", "")

        if not clip_path:
            issues.append(f"Scene {num}: no clip downloaded")
        elif not os.path.exists(clip_path):
            issues.append(f"Scene {num}: clip file missing - {clip_path}")
        elif os.path.getsize(clip_path) < 10000:
            issues.append(f"Scene {num}: clip file too small")

    return {"passed": len(issues) == 0, "issues": issues}


def check_scene_count(scenes: list) -> dict:
    issues = []

    if len(scenes) < 5:
        issues.append(f"Too few scenes: {len(scenes)} (need at least 5)")
    elif len(scenes) > 15:
        issues.append(f"Too many scenes: {len(scenes)} (max 15)")

    for scene in scenes:
        duration = scene.get("duration", 0)
        if duration < 2:
            issues.append(f"Scene {scene['scene_number']}: duration too short ({duration}s)")
        elif duration > 10:
            issues.append(f"Scene {scene['scene_number']}: duration too long ({duration}s)")

    return {"passed": len(issues) == 0, "issues": issues}


def check_total_duration(scenes: list) -> dict:
    issues = []
    total = sum(s.get("duration", 0) for s in scenes)

    if total < 30:
        issues.append(f"Video too short: {total}s (need 30-90s)")
    elif total > 90:
        issues.append(f"Video too long: {total}s (max 90s for Shorts)")

    return {"passed": len(issues) == 0, "issues": issues, "total_seconds": total}


def check_narration_quality(scenes: list) -> dict:
    issues = []

    for scene in scenes:
        narration = scene.get("narration", "")
        if len(narration) < 10:
            issues.append(f"Scene {scene['scene_number']}: narration too short")
        if len(narration.split()) > 50:
            issues.append(f"Scene {scene['scene_number']}: narration too long for duration")

    return {"passed": len(issues) == 0, "issues": issues}


def review_script(script_data: dict, research_data: dict) -> dict:
    log("REVIEW", f"Reviewing: {script_data['title']}")
    all_issues = []

    scenes = script_data.get("scenes", [])

    log("REVIEW", "Checking scene count...")
    result = check_scene_count(scenes)
    all_issues.extend(result["issues"])

    log("REVIEW", "Checking total duration...")
    result = check_total_duration(scenes)
    all_issues.extend(result["issues"])
    total_duration = result.get("total_seconds", 0)

    log("REVIEW", "Checking narration quality...")
    result = check_narration_quality(scenes)
    all_issues.extend(result["issues"])

    score = 10
    if len(all_issues) > 0:
        score -= len(all_issues) * 1
    if total_duration < 30 or total_duration > 90:
        score -= 2

    score = max(1, min(10, score))
    approved = score >= 6

    log("REVIEW", f"Score: {score}/10, Approved: {approved}")
    if all_issues:
        for issue in all_issues:
            log("REVIEW", f"  - {issue}")

    return {
        "score": score,
        "approved": approved,
        "issues": all_issues,
        "total_duration": total_duration,
        "scene_count": len(scenes)
    }


def review_assets(clips: list, voices: list, scenes: list) -> dict:
    log("REVIEW", "Checking downloaded assets...")
    all_issues = []

    log("REVIEW", "Checking audio files...")
    result = check_audio_files(scenes, voices)
    all_issues.extend(result["issues"])

    log("REVIEW", "Checking video clips...")
    result = check_clips(scenes, clips)
    all_issues.extend(result["issues"])

    score = 10
    if len(all_issues) > 0:
        score -= len(all_issues) * 2

    score = max(1, min(10, score))
    approved = score >= 5

    log("REVIEW", f"Assets Score: {score}/10, Approved: {approved}")
    if all_issues:
        for issue in all_issues:
            log("REVIEW", f"  - {issue}")

    return {
        "score": score,
        "approved": approved,
        "issues": all_issues
    }
