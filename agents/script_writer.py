import json
import re
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL
from utils.logger import log

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """You are a viral video script writer. Write a 60-second video script.

Return ONLY valid JSON (no extra text, no markdown, no code blocks):
{
  "title": "catchy YouTube title",
  "scenes": [
    {
      "scene_number": 1,
      "narration": "what the AI voice says",
      "clip_search_query": "search terms for stock video clip",
      "duration": 5
    }
  ],
  "tags": ["tag1", "tag2", "tag3"]
}

Rules:
- 8-12 scenes, each 4-8 seconds
- Hook viewers in first 3 seconds
- Each clip_search_query should be 2-4 words for stock video search
- Narration should be conversational and engaging
- Total narration ~150 words for 60 seconds"""


def clean_json(text: str) -> str:
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()
    return text


def parse_response(content: str) -> dict:
    cleaned = clean_json(content)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', cleaned)
        if match:
            return json.loads(match.group())
        raise


def write_script(topic_data: dict, retries: int = 3) -> dict:
    log("SCRIPT", f"Writing script for: {topic_data['topic']}")

    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Write a 60-second viral video script about: {topic_data['topic']}\nKeywords: {', '.join(topic_data['keywords'])}\nTarget audience: {topic_data['audience']}\n\nReturn ONLY valid JSON."}
                ],
                temperature=0.7,
                max_tokens=1500
            )

            content = response.choices[0].message.content
            result = parse_response(content)
            log("SCRIPT", f"Title: {result['title']}")
            log("SCRIPT", f"Scenes: {len(result['scenes'])}")
            return result

        except (json.JSONDecodeError, KeyError) as e:
            log("SCRIPT", f"Parse error (attempt {attempt + 1}/{retries}): {str(e)}")
            continue

    log("SCRIPT", "Failed to generate valid script after retries")
    return {
        "title": "Generated Video",
        "scenes": [{"scene_number": 1, "narration": "Welcome to this video.", "clip_search_query": "technology background", "duration": 5}],
        "tags": ["tech"]
    }
