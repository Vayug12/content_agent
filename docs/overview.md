# CreatorAgent — AI Short Video Generator

## What Is It?

CreatorAgent is an AI-powered short video generation platform. Users type a topic idea or paste a script, and the backend automatically produces a finished 60-second vertical MP4 video (YouTube Shorts / TikTok / Reels format) with stock footage, AI voiceover, text overlays, Ken Burns effects, and crossfade transitions.

**Scope:** Topic/script in → MP4 out. No publishing, no streaming, no analytics, no social features.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                   Flutter Mobile App                 │
│  (Topic input / Script input / Video playback /     │
│   Library / Progress polling / Sharing)              │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP (REST)
                       ▼
┌─────────────────────────────────────────────────────┐
│              FastAPI Backend (Python)                │
│              Port 7860, Dockerized                   │
│                                                     │
│  /topics/suggestions — AI topic ideas               │
│  /jobs — Create video job                           │
│  /jobs/{id} — Poll progress                         │
│  /jobs — List user library                          │
│  /jobs/{id} — Delete from library + R2              │
│  /health — Liveness check                           │
└──────────────────────┬──────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
┌──────────────┐ ┌──────────┐ ┌──────────────────┐
│   Groq LLM   │ │ Pexels / │ │ SQLite           │
│  llama-3.3-  │ │ Pixabay / │ │ video_jobs table │
│  70b-versatile│ │Wikimedia │ │ (auto-created)   │
└──────────────┘ └──────────┘ └──────────────────┘
                       │
                       ▼
              ┌──────────────────┐
              │  Cloudflare R2    │
              │ (S3-compatible)   │
              │ Videos auto-expire│
              └──────────────────┘
```

---

## Tech Stack

### Backend (`content_agent/`)

| Layer | Technology |
|---|---|
| Web framework | FastAPI + Uvicorn (port 7860) |
| LLM | Groq API — `llama-3.3-70b-versatile` |
| Text-to-Speech | Microsoft Edge TTS (`en-US-AriaNeural`) |
| Video editing | MoviePy (concat, Ken Burns, crossfades, text overlays, audio muxing) |
| Image processing | Pillow |
| Stock footage | Pexels (primary) → Pixabay (fallback) → Wikimedia Commons (no key) |
| Database | SQLite (single file, zero setup) |
| Object storage | Cloudflare R2 (S3-compatible via boto3) |
| Container | Docker (Python 3.11-slim + ffmpeg + fonts) |

### Frontend (`app/`)

| Layer | Technology |
|---|---|
| Framework | Flutter (Dart SDK ^3.9.0, Material 3) |
| HTTP | `http` + `dio` (video downloads with progress) |
| Identity | Anonymous device UUID via `shared_preferences` |
| Video playback | `video_player` |
| Sharing | `share_plus` (native OS share sheet) |
| Typography | `google_fonts` (Inter) |
| File storage | `path_provider` (app documents dir for cached videos) |

---

## Video Generation Pipeline

### Topic-to-Video
1. **Topic suggestion** — Groq LLM generates category-specific topic ideas (15 categories)
2. **Prompt enhancement** — User idea → structured topic with category, keywords, audience, hook
3. **Research** — LLM generates facts, statistics, trends, examples, controversial angles
4. **Script writing** — LLM writes 8-12 scene, ~60s narration script with stock footage search queries
5. **Clip fetching** — Pexels (portrait-first) → Pixabay → Wikimedia Commons. Rate limiting, retry, 30MB cap
6. **Voice generation** — Edge TTS per-scene MP3 files
7. **Video editing** — MoviePy: Ken Burns zoom, center-crop for portrait, text overlays, 0.5s crossfades
8. **Upload** — Final MP4 → Cloudflare R2 → URL returned to app

### Script-to-Video (alternative)
- User pastes their own script
- LLM splits into scenes preserving user's exact words
- Duration calculated from word count (2.5 words/sec)
- Same downstream pipeline

---

## API Reference

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `GET` | `/topics/suggestions` | AI topic ideas for picker |
| `POST` | `/jobs` | Queue video generation job |
| `GET` | `/jobs/{job_id}` | Poll job progress |
| `GET` | `/jobs` | User's library |
| `DELETE` | `/jobs/{job_id}` | Remove from library + R2 |

All endpoints except `/health` require `X-API-Key` header when `API_KEY` is set.

### Job Lifecycle

```
queued → scripting → clips → voice → rendering → uploading → done
```

**Statuses:** `queued` | `processing` | `completed` | `failed`

### Validation Rules
- Either `prompt` or `script` must be provided (400 if both empty)
- User script capped at 5000 characters (400 if exceeded)
- R2 must be configured or 503 is returned

---

## Mobile App Screens

1. **Hub Screen** — Central input with toggle: "Topic" mode (AI suggestion chips) or "My Script" mode (5000-char textarea)
2. **Generating Screen** — Real-time progress polling (every 3s), shows pipeline stages, user can leave and return
3. **Video Detail Screen** — Downloads video to device, plays in-app with looping, share button (native OS share sheet)
4. **Library Screen** — Past jobs list with status pills, pull-to-refresh, delete with confirmation

### Design System
- ChatGPT/Apple/Linear/Notion-inspired minimal aesthetic
- 8-point grid spacing system
- Single green accent: `#10A37F`
- Light-only (no dark mode)
- Skeleton loading, empty states, error views

---

## Deployment

### Backend
```bash
# Local
pip install -r requirements.txt
cp .env.example .env  # fill in keys
python api.py

# Docker
docker build . -t creatoragent
docker run -p 7860:7860 creatoragent
```

### Frontend
```bash
flutter run --dart-define=API_BASE_URL=http://YOUR_API_URL:7860
flutter build apk --dart-define=API_BASE_URL=https://YOUR_API_URL
```

### Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `GROQ_API_KEY` | Yes | Groq LLM access |
| `R2_ACCOUNT_ID` | Yes | Cloudflare R2 storage |
| `R2_ACCESS_KEY_ID` | Yes | R2 auth |
| `R2_SECRET_ACCESS_KEY` | Yes | R2 auth |
| `R2_BUCKET` | Yes | R2 bucket name |
| `R2_PUBLIC_BASE_URL` | No | Permanent URLs (otherwise presigned) |
| `R2_RETENTION_DAYS` | No | Auto-delete after N days (default 7) |
| `API_KEY` | No | Shared secret for API access |
| `PEXELS_API_KEY` | No | Primary clip source |
| `PIXABAY_API_KEY` | No | Fallback clip source |
| `DB_PATH` | No | SQLite file path (default: `data/creatoragent.db`) |

---

## Storage Architecture

- **R2 is a handoff buffer, not a library.** Videos auto-expire via lifecycle rule. Job metadata persists in SQLite.
- **No egress costs** on R2. ~15MB per 60s video.
- **Presigned URLs** have a hard 7-day max (SigV4 limit). Set `R2_PUBLIC_BASE_URL` for permanent URLs.
- At 100 videos/day with 7-day retention: ~$0.15/month storage cost.

---

## Known Limitations (Intentional)

- No real authentication (user_id is whatever the caller sends)
- No rate limiting or quotas
- No moderation on prompts/scripts
- Single worker per process (no concurrent renders)
- Groq free tier rate limits under concurrent users
