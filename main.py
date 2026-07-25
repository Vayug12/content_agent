import json
import os
import sys
import glob
from config import OUTPUT_DIR
from agents.topic_selector import select_topic
from agents.research_agent import research_topic
from agents.script_writer import write_script
from agents.review_agent import review_script, review_assets
from agents.clip_fetcher import fetch_all_clips
from agents.voice_generator import generate_all_voices
from agents.video_editor import edit_video
from agents.publishing_agent import generate_metadata, publish_to_vayug
from agents.analytics_agent import analyze_performance
from agents.prompt_enhancer import enhance_prompt
from utils.logger import log
from utils.memory import add_to_memory, get_memory_stats, add_pipeline_run


def cleanup_temp_files():
    import time

    patterns = [
        os.path.join(OUTPUT_DIR, "clip_*.mp4"),
        os.path.join(OUTPUT_DIR, "voice_*.mp3"),
        os.path.join(OUTPUT_DIR, "scene_*.mp4"),
        os.path.join(OUTPUT_DIR, "concat.txt"),
    ]

    time.sleep(2)

    deleted = 0
    for pattern in patterns:
        for filepath in glob.glob(pattern):
            try:
                os.remove(filepath)
                deleted += 1
            except PermissionError:
                pass

    log("CLEANUP", f"Removed {deleted} temporary files")


def run_pipeline():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    log("PIPELINE", "=" * 50)
    log("PIPELINE", "STARTING AI CONTENT AGENT")
    log("PIPELINE", "=" * 50)

    stats = get_memory_stats()
    log("PIPELINE", f"Previous runs: {stats['total_runs']}, Topics used: {stats['topics_used']}")

    # Step 1: Trend Agent - Select trending topic
    log("PIPELINE", "Step 1/7: Trend Agent")
    topic_data = select_topic()
    add_to_memory(topic_data)

    # Step 2: Research Agent - Research the topic
    log("PIPELINE", "Step 2/7: Research Agent")
    research_data = research_topic(topic_data)

    # Step 3: Content Agent - Write script
    log("PIPELINE", "Step 3/7: Content Agent")
    topic_data["research"] = research_data
    script_data = write_script(topic_data)

    # Step 4: Review Agent - Review the script
    log("PIPELINE", "Step 4/7: Review Agent")
    review_result = review_script(script_data, research_data)
    log("PIPELINE", f"Review Score: {review_result['score']}/10")

    if not review_result["approved"] and review_result["score"] < 5:
        log("PIPELINE", "Script rejected, regenerating...")
        script_data = write_script(topic_data)
        review_result = review_script(script_data, research_data)
        log("PIPELINE", f"New Review Score: {review_result['score']}/10")

    # Save script
    script_path = os.path.join(OUTPUT_DIR, "script.json")
    with open(script_path, "w") as f:
        json.dump(script_data, f, indent=2)

    scenes = script_data["scenes"]

    # Step 5: Content Agent - Fetch clips and generate voice
    log("PIPELINE", "Step 5/7: Content Agent (Assets)")
    clips = fetch_all_clips(scenes)
    voices = generate_all_voices(scenes)

    # Step 5.5: Review Agent - Check assets
    log("PIPELINE", "Step 5.5: Review Agent (Assets Check)")
    asset_review = review_assets(clips, voices, scenes)
    if not asset_review["approved"]:
        log("PIPELINE", f"Asset review failed with {len(asset_review['issues'])} issues")

    # Step 6: Content Agent - Edit video
    log("PIPELINE", "Step 6/7: Content Agent (Editing)")
    final_video = edit_video(scenes, clips, voices)

    # Step 7: Publishing Agent - Generate metadata
    log("PIPELINE", "Step 7/7: Publishing Agent")
    if final_video:
        metadata = generate_metadata(script_data, research_data)
        metadata_path = os.path.join(OUTPUT_DIR, "metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        # Publish to Vayug app
        publish_result = publish_to_vayug(final_video, metadata)

        # Sirf data save karo (video URL, title, tags)
        add_pipeline_run(
            topic=topic_data["topic"],
            title=metadata.get("title", ""),
            tags=metadata.get("tags", []),
            video_url=publish_result.get("video", {}).get("videoUrl", ""),
            status="success"
        )

        # Video DELETE karo (storage save karo)
        if os.path.exists(final_video):
            os.remove(final_video)
            log("PIPELINE", "Video file deleted (data saved to Supabase)")
    else:
        metadata = {}
        publish_result = {}
        add_pipeline_run(
            topic=topic_data["topic"],
            title="",
            tags=[],
            video_url="",
            status="failed"
        )

    # Cleanup
    cleanup_temp_files()

    log("PIPELINE", "=" * 50)
    log("PIPELINE", "PIPELINE COMPLETE")
    if final_video:
        log("PIPELINE", f"Final video: {final_video}")
        log("PIPELINE", f"Title: {metadata.get('title', 'N/A')}")
    else:
        log("PIPELINE", "No video produced")
    log("PIPELINE", "=" * 50)

    return {
        "topic": topic_data,
        "script": script_data,
        "video": final_video,
        "metadata": metadata,
        "review": review_result,
        "publish": publish_result
    }


def run_pipeline_from_prompt(user_prompt: str, category: str = None, audience: str = None):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    log("PIPELINE", "=" * 50)
    log("PIPELINE", "STARTING PROMPT-TO-VIDEO PIPELINE")
    log("PIPELINE", "=" * 50)

    # Step 0: Enhance user prompt into full topic_data
    log("PIPELINE", "Step 0/7: Enhancing User Prompt")
    topic_data = enhance_prompt(user_prompt, category, audience)
    add_to_memory(topic_data)

    # Step 1: Research Agent - Research the topic
    log("PIPELINE", "Step 1/7: Research Agent")
    research_data = research_topic(topic_data)

    # Step 2: Content Agent - Write script
    log("PIPELINE", "Step 2/7: Content Agent")
    topic_data["research"] = research_data
    script_data = write_script(topic_data)

    # Step 3: Review Agent - Review the script
    log("PIPELINE", "Step 3/7: Review Agent")
    review_result = review_script(script_data, research_data)
    log("PIPELINE", f"Review Score: {review_result['score']}/10")

    if not review_result["approved"] and review_result["score"] < 5:
        log("PIPELINE", "Script rejected, regenerating...")
        script_data = write_script(topic_data)
        review_result = review_script(script_data, research_data)
        log("PIPELINE", f"New Review Score: {review_result['score']}/10")

    # Save script
    script_path = os.path.join(OUTPUT_DIR, "script.json")
    with open(script_path, "w") as f:
        json.dump(script_data, f, indent=2)

    scenes = script_data["scenes"]

    # Step 4: Content Agent - Fetch clips and generate voice
    log("PIPELINE", "Step 4/7: Content Agent (Assets)")
    clips = fetch_all_clips(scenes)
    voices = generate_all_voices(scenes)

    # Step 4.5: Review Agent - Check assets
    log("PIPELINE", "Step 4.5: Review Agent (Assets Check)")
    asset_review = review_assets(clips, voices, scenes)
    if not asset_review["approved"]:
        log("PIPELINE", f"Asset review failed with {len(asset_review['issues'])} issues")

    # Step 5: Content Agent - Edit video
    log("PIPELINE", "Step 5/7: Content Agent (Editing)")
    final_video = edit_video(scenes, clips, voices)

    # Step 6: Publishing Agent - Generate metadata
    log("PIPELINE", "Step 6/7: Publishing Agent")
    if final_video:
        metadata = generate_metadata(script_data, research_data)
        metadata_path = os.path.join(OUTPUT_DIR, "metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        publish_result = publish_to_vayug(final_video, metadata)

        add_pipeline_run(
            topic=topic_data["topic"],
            title=metadata.get("title", ""),
            tags=metadata.get("tags", []),
            video_url=publish_result.get("video", {}).get("videoUrl", ""),
            status="success"
        )

        if os.path.exists(final_video):
            os.remove(final_video)
            log("PIPELINE", "Video file deleted (data saved to Supabase)")
    else:
        metadata = {}
        publish_result = {}
        add_pipeline_run(
            topic=topic_data["topic"],
            title="",
            tags=[],
            video_url="",
            status="failed"
        )

    # Cleanup
    cleanup_temp_files()

    log("PIPELINE", "=" * 50)
    log("PIPELINE", "PROMPT-TO-VIDEO PIPELINE COMPLETE")
    if final_video:
        log("PIPELINE", f"Final video: {final_video}")
        log("PIPELINE", f"Title: {metadata.get('title', 'N/A')}")
    else:
        log("PIPELINE", "No video produced")
    log("PIPELINE", "=" * 50)

    return {
        "topic": topic_data,
        "script": script_data,
        "video": final_video,
        "metadata": metadata,
        "review": review_result,
        "publish": publish_result
    }


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Prompt mode: python main.py "your prompt here"
        user_prompt = " ".join(sys.argv[1:])
        run_pipeline_from_prompt(user_prompt)
    else:
        # Default: autonomous topic selection
        run_pipeline()
