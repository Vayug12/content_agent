import time
import schedule
from datetime import datetime
from utils.logger import log
from main import run_pipeline
from agents.analytics_agent import analyze_performance
from utils.memory import add_pipeline_run


def daily_analytics():
    log("SCHEDULER", "Running daily analytics...")
    try:
        analyze_performance()
    except Exception as e:
        log("SCHEDULER", f"Analytics error: {str(e)}")


def run_content_pipeline():
    log("SCHEDULER", f"Starting pipeline at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        result = run_pipeline()
        return result
    except Exception as e:
        log("SCHEDULER", f"Pipeline error: {str(e)}")
        return None


def start_scheduler(videos_per_day: int = 2, interval_hours: int = 4):
    log("SCHEDULER", "=" * 50)
    log("SCHEDULER", "STARTING AUTONOMOUS AGENT")
    log("SCHEDULER", f"Videos per day: {videos_per_day}")
    log("SCHEDULER", f"Interval: {interval_hours} hours")
    log("SCHEDULER", "=" * 50)

    schedule.every().day.at("09:00").do(run_content_pipeline)
    schedule.every().day.at("13:00").do(run_content_pipeline)
    schedule.every().day.at("17:00").do(run_content_pipeline)
    schedule.every().day.at("21:00").do(run_content_pipeline)

    if videos_per_day > 4:
        schedule.every().day.at("11:00").do(run_content_pipeline)
        schedule.every().day.at("15:00").do(run_content_pipeline)
        schedule.every().day.at("19:00").do(run_content_pipeline)

    schedule.every().day.at("23:00").do(daily_analytics)

    log("SCHEDULER", "Scheduler started. Waiting for next run...")
    log("SCHEDULER", "Press Ctrl+C to stop")

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    import sys
    videos = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    start_scheduler(videos_per_day=videos)
