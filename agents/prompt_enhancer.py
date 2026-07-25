import json
import re
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL
from utils.logger import log

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """You are a video topic enhancer. Take a user's simple prompt/idea and transform it into a structured video topic.

Return JSON only:
{
  "topic": "enhanced, specific, viral-worthy topic string",
  "category": "category name (e.g., AI Engineering, Web Development, Cybersecurity, etc.)",
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
  "audience": "target audience description",
  "hook": "first 3 second attention-grabbing line"
}

Rules:
- Keep the user's original intent but make it more specific and engaging
- Make it viral-worthy and interesting for YouTube Shorts
- Choose the most relevant category from: Software Engineering, AI Engineering, Tech News, Startup & Business, Web Development, Mobile App Development, Cybersecurity, Cloud Computing & DevOps, Data Science, Programming Tips & Tricks, Future Technology, Open Source Tools, Career in Tech, Productivity for Developers, AI Tools & Automation
- Generate 5 relevant SEO keywords
- Define a clear target audience
- Create a compelling hook for the first 3 seconds
- Must be relevant to 2026
- Return ONLY valid JSON, no extra text"""


def enhance_prompt(user_prompt: str, category: str = None, audience: str = None) -> dict:
    """Transform a user's simple prompt into a full topic_data structure."""
    log("PROMPT", f"Enhancing user prompt: {user_prompt}")

    user_content = f"User's prompt/idea: {user_prompt}"
    if category:
        user_content += f"\nPreferred category: {category}"
    if audience:
        user_content += f"\nTarget audience: {audience}"
    user_content += "\n\nTransform this into a structured video topic. Return JSON only."

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.7,
                max_tokens=500
            )

            content = response.choices[0].message.content
            cleaned = re.sub(r'```json\s*', '', content)
            cleaned = re.sub(r'```\s*', '', cleaned)
            match = re.search(r'\{[\s\S]*\}', cleaned)

            if match:
                result = json.loads(match.group())
            else:
                result = json.loads(cleaned)

            log("PROMPT", f"Enhanced topic: {result['topic']}")
            log("PROMPT", f"Category: {result['category']}")
            log("PROMPT", f"Keywords: {result['keywords']}")
            return result

        except (json.JSONDecodeError, KeyError) as e:
            log("PROMPT", f"Parse error (attempt {attempt + 1}/3): {str(e)}")
            continue

    log("PROMPT", "Failed to enhance prompt, using basic fallback")
    return {
        "topic": user_prompt,
        "category": category or "Unknown",
        "keywords": user_prompt.split()[:5],
        "audience": audience or "Tech enthusiasts",
        "hook": f"Did you know about {user_prompt}?"
    }
