from datetime import datetime


def log(stage: str, message: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{stage}] {message}")
