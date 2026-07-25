import json
import random
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL
from utils.logger import log
from utils.memory import get_used_topics

client = Groq(api_key=GROQ_API_KEY)

CATEGORIES = [
    "Software Engineering",
    "AI Engineering",
    "Tech News",
    "Startup & Business",
    "Web Development",
    "Mobile App Development",
    "Cybersecurity",
    "Cloud Computing & DevOps",
    "Data Science",
    "Programming Tips & Tricks",
    "Future Technology",
    "Open Source Tools",
    "Career in Tech",
    "Productivity for Developers",
    "AI Tools & Automation"
]

SYSTEM_PROMPT = """You are a YouTube Shorts topic selector for a tech-focused channel.
Return JSON only:
{
  "topic": "specific topic string",
  "category": "category name from the list provided",
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
  "audience": "target audience",
  "hook": "first 3 second attention-grabbing line"
}

Rules:
- Topic must be specific and actionable (not generic)
- Must be relevant to 2026
- Should make viewers think "I didn't know this" or "I need this"
- Keep it viral-worthy and interesting
- DO NOT repeat any topics from the "Already used topics" list
- Examples of good topics:
  - "5 VS Code Extensions That Save 10 Hours/Week"
  - "Why Rust is Replacing C++ in 2026"
  - "How I Built a SaaS in 7 Days Using AI"
  - "The AI Tool That Replaced My Entire Dev Team"
  - "Linux Commands Every Developer Must Know"
"""


def select_topic() -> dict:
    log("TOPIC", "Selecting trending topic...")

    category = random.choice(CATEGORIES)
    log("TOPIC", f"Category: {category}")

    used_topics = get_used_topics()
    used_text = "\n".join([f"- {t}" for t in used_topics[-20:]]) if used_topics else "None yet"

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Category: {category}\n\nAlready used topics (DO NOT repeat these):\n{used_text}\n\nPick a NEW, unique, viral-worthy topic for a 60-second YouTube Short. Return JSON only."}
        ],
        temperature=0.9,
        max_tokens=400
    )

    result = json.loads(response.choices[0].message.content)
    log("TOPIC", f"Selected: {result['topic']}")
    return result
