import os
from dotenv import load_dotenv

load_dotenv()

# ==================== KEYS ====================

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "")

# Shared secret between the app and this service.
# Khaali chhoda toh API bilkul open rahegi - production me set karo.
API_KEY = os.getenv("API_KEY", "")

# SQLite — ek file, zero setup, data restart pe safe
DB_PATH = os.getenv("DB_PATH", "data/creatoragent.db")

# Cloudflare R2 - finished videos yahan store hote hai
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET = os.getenv("R2_BUCKET", "")
# Public bucket / custom domain ho toh permanent URLs, warna presigned.
R2_PUBLIC_BASE_URL = os.getenv("R2_PUBLIC_BASE_URL", "").rstrip("/")

# R2 sirf handoff buffer hai, library nahi. Itne din baad lifecycle rule
# object khud delete kar deta hai. Presigned link expiry bhi isi se banti hai,
# isliye link aur file kabhi desync nahi hote. setup_r2.py se rule apply karo.
R2_RETENTION_DAYS = int(os.getenv("R2_RETENTION_DAYS", "7"))
R2_OBJECT_PREFIX = "videos/"

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env file. Get free key at https://console.groq.com")

# ==================== GENERATION ====================

GROQ_MODEL = "llama-3.3-70b-versatile"
VOICE = "en-US-AriaNeural"

# Har job apni subdirectory me kaam karta hai: output/<job_id>/
# Isse do users ki files kabhi collide nahi hoti.
OUTPUT_DIR = "output"

# Output portrait hai (shorts format)
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

# ==================== CLIPS ====================
# Pexels -> Pixabay -> Wikimedia Commons

CLIP_MAX_FILESIZE = 30 * 1024 * 1024  # 30MB per clip
CLIP_SEARCH_COUNT = 3  # Candidates per source, per scene
CLIP_MIN_HEIGHT = 720  # Prefer smallest file at or above this height

# ==================== VIDEO EDITING ====================

KEN_BURNS_ZOOM = 1.03  # 3% zoom effect (subtle)
CROSSFADE_DURATION = 0.5  # 0.5 second transition
TEXT_OVERLAY_FONT = "Arial-Bold"
TEXT_OVERLAY_SIZE = 28  # Small, subtle
TEXT_OVERLAY_MAX_WORDS = 3  # Keywords only

# ==================== LIMITS ====================

MAX_SCRIPT_CHARS = 5000  # User-supplied script cap
