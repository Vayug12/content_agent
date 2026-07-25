import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
VAYUG_JWT = os.getenv("VAYUG_JWT", "")
VAYUG_API_BASE = os.getenv("VAYUG_API_BASE", "https://api.snehayog.site")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env file. Get free key at https://console.groq.com")
if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL not found in .env file. Get free key at https://supabase.com")
if not SUPABASE_KEY:
    raise ValueError("SUPABASE_KEY not found in .env file. Get free key at https://supabase.com")

GROQ_MODEL = "llama-3.3-70b-versatile"
OUTPUT_DIR = "output"
VOICE = "en-US-AriaNeural"
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080

# YouTube Settings
YOUTUBE_MAX_FILESIZE = 30 * 1024 * 1024  # 30MB limit
YOUTUBE_SEARCH_COUNT = 5  # Results per search
YOUTUBE_MIN_DURATION = 10  # Min video duration (seconds)
YOUTUBE_MAX_DURATION = 900  # Max video duration (seconds) - 15 min
YOUTUBE_MAX_HEIGHT = 720  # Max video height (720p for size control)

# Video Editing Settings
KEN_BURNS_ZOOM = 1.03  # 3% zoom effect (subtle)
CROSSFADE_DURATION = 0.5  # 0.5 second transition
TEXT_OVERLAY_FONT = "Arial-Bold"
TEXT_OVERLAY_SIZE = 28  # Small, subtle
TEXT_OVERLAY_MAX_WORDS = 3  # Keywords only
