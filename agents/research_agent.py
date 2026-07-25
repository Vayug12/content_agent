import json
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL
from utils.logger import log

client = Groq(api_key=GROQ_API_KEY)


def research_topic(topic_data: dict) -> dict:
    log("RESEARCH", f"Researching: {topic_data['topic']}")

    SYSTEM_PROMPT = """You are a research agent. Research the given topic and provide:
1. Key facts and statistics
2. Current trends
3. Expert opinions
4. Real examples
5. Controversial angles

Return JSON only:
{
  "facts": ["fact1", "fact2", "fact3", "fact4", "fact5"],
  "statistics": [{"stat": "statistic", "source": "source"}],
  "trends": ["trend1", "trend2"],
  "examples": ["example1", "example2"],
  "angles": ["angle1", "angle2"]
}"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Research this topic thoroughly:\n\nTopic: {topic_data['topic']}\nCategory: {topic_data.get('category', 'Unknown')}\nKeywords: {', '.join(topic_data.get('keywords', []))}\n\nReturn JSON only."}
        ],
        temperature=0.5,
        max_tokens=1500
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
        log("RESEARCH", f"Found {len(result.get('facts', []))} facts")
        return result
    except:
        log("RESEARCH", "Research parse failed, using defaults")
        return {
            "facts": [topic_data["topic"]],
            "statistics": [],
            "trends": [],
            "examples": [],
            "angles": []
        }
