import json
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL
from utils.logger import log
from utils.memory import get_all_topics, get_memory_stats

client = Groq(api_key=GROQ_API_KEY)


def analyze_performance() -> dict:
    log("ANALYTICS", "Analyzing performance...")

    stats = get_memory_stats()
    recent_topics = get_all_topics(limit=10)

    SYSTEM_PROMPT = """You are an analytics agent. Analyze the content performance and suggest improvements.

Return JSON only:
{
  "total_videos": 10,
  "category_distribution": {"Software Engineering": 3, "AI Engineering": 4},
  "top_performing_topics": ["topic1", "topic2"],
  "recommendations": ["rec1", "rec2", "rec3"],
  "best_time_to_post": "suggested time",
  "content_gaps": ["gap1", "gap2"]
}"""

    topics_text = "\n".join([f"- {t['topic']} ({t['category']})" for t in recent_topics])

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze this content history:\n\nTotal runs: {stats['total_runs']}\nTopics used: {stats['topics_used']}\n\nRecent topics:\n{topics_text}\n\nReturn JSON only."}
        ],
        temperature=0.5,
        max_tokens=800
    )

    try:
        content = response.choices[0].message.content
        import re
        cleaned = re.sub(r'```json\s*', '', content)
        cleaned = re.sub(r'```\s*', '', cleaned)
        match = re.search(r'\{[\s\S]*\}', cleaned)
        if match:
            result = json.loads(match.group())
        else:
            result = json.loads(cleaned)
        log("ANALYTICS", f"Recommendations: {len(result.get('recommendations', []))}")
        return result
    except:
        log("ANALYTICS", "Analytics parse failed")
        return {
            "total_videos": stats["total_runs"],
            "recommendations": ["Continue posting regularly", "Mix up categories"],
            "content_gaps": []
        }
