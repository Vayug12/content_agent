"""Topic suggestions for the picker screen.

Pehle ye autonomous channel ke liye ek topic choose karta tha (globally used
topics avoid karke). Ab user choose karta hai, isliye ye sirf suggestions deta hai.
"""

import json
import re
import random
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL
from utils.logger import log

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
    "AI Tools & Automation",
]

SYSTEM_PROMPT = """You suggest short-form video topics a creator can make in 60 seconds.

Return JSON only:
{
  "topics": [
    {"topic": "specific topic string", "category": "category name", "hook": "first 3 second attention-grabbing line"}
  ]
}

Rules:
- Each topic must be specific and actionable, never generic
- Should make viewers think "I didn't know this" or "I need this"
- Vary the angle across suggestions - do not return near-duplicates
- Return ONLY valid JSON, no extra text"""


def suggest_topics(count: int = 6, category: str = None) -> list:
    """Picker screen ke liye topic suggestions."""
    chosen = category or random.choice(CATEGORIES)
    log("TOPIC", f"Suggesting {count} topics for: {chosen}")

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Category: {chosen}\n\nSuggest {count} topics. Return JSON only."}
            ],
            temperature=0.9,
            max_tokens=800
        )

        content = response.choices[0].message.content
        match = re.search(r'\{[\s\S]*\}', re.sub(r'```(json)?', '', content))
        result = json.loads(match.group() if match else content)

        topics = result.get("topics", [])[:count]
        log("TOPIC", f"Suggested {len(topics)} topics")
        return topics

    except (json.JSONDecodeError, KeyError, AttributeError) as e:
        log("TOPIC", f"Suggestion error: {str(e)}")
        return []
