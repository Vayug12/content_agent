import asyncio
import edge_tts
from config import VOICE
from utils.logger import log
import os


async def generate_voice(text: str, filename: str, out_dir: str) -> str:
    output_path = os.path.join(out_dir, filename)
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(output_path)
    return output_path


def generate_all_voices(scenes: list, out_dir: str) -> list:
    log("VOICE", "Generating AI voices...")
    results = []

    for scene in scenes:
        filename = f"voice_{scene['scene_number']}.mp3"
        log("VOICE", f"Scene {scene['scene_number']}: generating voice...")

        path = asyncio.run(generate_voice(scene["narration"], filename, out_dir))
        results.append({
            "scene_number": scene["scene_number"],
            "path": path
        })

    log("VOICE", f"Generated {len(results)} voice files")
    return results
