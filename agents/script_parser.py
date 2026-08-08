"""User ka apna script -> scenes.

Ye doosra entry point hai: user khud script likhta hai, toh research aur
script_writer skip ho jaate hai. Output schema wahi hai jo script_writer deta
hai, isliye clip_fetcher aur video_editor me kuch change nahi karna padta.
"""

import json
import re
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL, MAX_SCRIPT_CHARS
from utils.logger import log

client = Groq(api_key=GROQ_API_KEY)

# Speaking pace - duration LLM se nahi, word count se nikalte hai (zyada reliable)
WORDS_PER_SECOND = 2.5
MIN_SCENE_DURATION = 3.0
MAX_SCENE_DURATION = 10.0

SYSTEM_PROMPT = """You split a narration script into video scenes.

Return JSON only:
{
  "title": "short video title",
  "tags": ["tag1", "tag2", "tag3"],
  "scenes": [
    {"narration": "exact text from the script for this scene",
     "clip_search_query": "2-4 word visual search query for stock footage"}
  ]
}

Rules:
- Use the user's words VERBATIM in narration. Never rewrite, shorten, or improve them.
- Every word of the script must appear in exactly one scene, in order.
- Split at natural sentence boundaries, roughly one idea per scene.
- clip_search_query describes what should be shown on screen, not what is said.
  It must be concrete and visual ("server room racks", not "scalability").
- Return ONLY valid JSON, no extra text"""


def estimate_duration(text: str) -> float:
    """Word count se scene duration - clamp karke rakho."""
    words = len(text.split())
    return max(MIN_SCENE_DURATION, min(MAX_SCENE_DURATION, words / WORDS_PER_SECOND))


def parse_script(script_text: str, title: str = "") -> dict:
    """User ke script ko scenes me todo."""
    script_text = (script_text or "").strip()
    if not script_text:
        raise ValueError("Script is empty")
    if len(script_text) > MAX_SCRIPT_CHARS:
        raise ValueError(f"Script too long ({len(script_text)} chars, max {MAX_SCRIPT_CHARS})")

    log("PARSE", f"Splitting user script ({len(script_text.split())} words)")

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Script:\n{script_text}\n\nSplit into scenes. Return JSON only."}
                ],
                temperature=0.3,  # Verbatim chahiye, isliye low temperature
                max_tokens=2000
            )

            content = response.choices[0].message.content
            match = re.search(r'\{[\s\S]*\}', re.sub(r'```(json)?', '', content))
            result = json.loads(match.group() if match else content)

            scenes = []
            for i, scene in enumerate(result.get("scenes", []), start=1):
                narration = (scene.get("narration") or "").strip()
                if not narration:
                    continue
                scenes.append({
                    "scene_number": i,
                    "narration": narration,
                    "duration": estimate_duration(narration),
                    "clip_search_query": scene.get("clip_search_query") or title or "abstract background",
                })

            if not scenes:
                raise ValueError("No usable scenes returned")

            log("PARSE", f"Split into {len(scenes)} scenes")
            return {
                "title": title or result.get("title", "Untitled"),
                "tags": result.get("tags", []),
                "scenes": scenes,
            }

        except (json.JSONDecodeError, KeyError, AttributeError, ValueError) as e:
            log("PARSE", f"Parse error (attempt {attempt + 1}/3): {str(e)}")
            continue

    # Fallback: sentences pe split karke chala lo, LLM ke bina
    log("PARSE", "LLM split failed, falling back to sentence split")
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', script_text) if s.strip()]
    scenes = [
        {
            "scene_number": i,
            "narration": s,
            "duration": estimate_duration(s),
            "clip_search_query": title or "abstract background",
        }
        for i, s in enumerate(sentences, start=1)
    ]
    return {"title": title or "Untitled", "tags": [], "scenes": scenes}
