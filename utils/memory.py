from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY
from utils.logger import log

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def add_to_memory(topic_data: dict):
    try:
        supabase.table("topics").insert({
            "topic": topic_data["topic"],
            "category": topic_data.get("category", ""),
            "title": topic_data.get("title", "")
        }).execute()
        log("MEMORY", f"Saved topic: {topic_data['topic']}")
    except Exception as e:
        log("MEMORY", f"Error saving topic: {str(e)}")


def get_used_topics() -> list:
    try:
        result = supabase.table("topics") \
            .select("topic") \
            .order("id", desc=True) \
            .limit(50) \
            .execute()
        return [t["topic"] for t in result.data]
    except Exception as e:
        log("MEMORY", f"Error fetching topics: {str(e)}")
        return []


def get_memory_stats() -> dict:
    try:
        topics_result = supabase.table("topics") \
            .select("id", count="exact") \
            .execute()
        runs_result = supabase.table("pipeline_runs") \
            .select("id", count="exact") \
            .execute()
        return {
            "total_runs": runs_result.count or 0,
            "topics_used": topics_result.count or 0
        }
    except Exception as e:
        log("MEMORY", f"Error fetching stats: {str(e)}")
        return {"total_runs": 0, "topics_used": 0}


def add_pipeline_run(topic: str, title: str, tags: list, video_url: str, status: str):
    try:
        supabase.table("pipeline_runs").insert({
            "topic": topic,
            "title": title,
            "tags": tags,
            "video_url": video_url,
            "status": status
        }).execute()
        log("MEMORY", f"Saved pipeline run: {topic}")
    except Exception as e:
        log("MEMORY", f"Error saving pipeline run: {str(e)}")


def get_all_topics(limit: int = 100) -> list:
    try:
        result = supabase.table("topics") \
            .select("*") \
            .order("id", desc=True) \
            .limit(limit) \
            .execute()
        return result.data
    except Exception as e:
        log("MEMORY", f"Error fetching all topics: {str(e)}")
        return []
