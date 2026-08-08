# Content Agent

Generates short vertical videos from a topic or a user's own script. The user
picks a suggested topic, types their own idea, or pastes a full script — the
service returns an MP4 they can download or share.

That is the whole product. No publishing, no streaming, no analytics.

## How it works

```
POST /jobs  →  queued in Supabase  →  worker claims it
                                          │
        ┌─────────────────────────────────┴──────────────────────────────┐
        │ prompt path:  enhance → research → write script                │
        │ script path:  parse user's script into scenes (verbatim)       │
        └─────────────────────────────────┬──────────────────────────────┘
                                          │
                   clips → voice → render → upload to R2
                                          │
                              GET /jobs/{id} → video_url
```

Each job renders inside `output/<job_id>/` and that directory is deleted when
the job ends, pass or fail. Nothing is shared between jobs.

## Why videos touch R2 at all

Rendering is asynchronous — it takes minutes, and no phone holds an HTTP
connection open that long. So the finished file has to wait somewhere between
"render done" and "user opens the app and taps Download." Container disk cannot
be that place: it is ephemeral, it resets when the instance sleeps, and it is
invisible to a second worker.

**R2 is a handoff buffer, not a library.** A lifecycle rule deletes each video
after `R2_RETENTION_DAYS`. The job row keeps the title and date so the user's
history still lists what they made — only the file goes away.

Sharing uses the Android share sheet, so the app downloads the MP4 to the device
and shares a local `content://` URI. **The R2 URL never leaves the owner's
device**, which is why a short retention window breaks nothing.

Cost is negligible: R2 is $0.015/GB-month with **zero egress**, and a 60-second
vertical video is roughly 15MB. At 100 videos/day with 7-day retention that is
about 10GB, or roughly $0.15/month. Render CPU remains the real cost.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness + whether storage is configured |
| `GET` | `/topics/suggestions` | Topics for the picker screen |
| `POST` | `/jobs` | Queue a generation (`prompt` and/or `script`) |
| `GET` | `/jobs/{id}` | Poll status and stage |
| `GET` | `/jobs` | The user's library |
| `DELETE` | `/jobs/{id}` | Remove from library, delete from R2 |

All endpoints except `/health` require an `X-API-Key` header when `API_KEY` is set.

Job stages, in order: `queued → scripting → clips → voice → rendering → uploading → done`.

## Clip sources

Tried in order, first success wins:

1. **Pexels** — needs `PEXELS_API_KEY`
2. **Pixabay** — needs `PIXABAY_API_KEY`
3. **Wikimedia Commons** — no key

Attribution for every clip is written to `attributions.json` during the run.
Commons content is CC-BY/CC-BY-SA, so if you surface these videos publicly you
need to carry that credit through to the user.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env      # fill in the keys
# run schema.sql once in the Supabase SQL editor
python setup_r2.py        # applies the R2 lifecycle rule (safe to re-run)
python api.py
```

Requires `ffmpeg` on PATH (the Dockerfile installs it).

`setup_r2.py` is idempotent — re-run it any time you change `R2_RETENTION_DAYS`.
It also expires incomplete multipart uploads after a day, which otherwise
accumulate silently and get billed.

## Environment

| Variable | Required | Notes |
|---|---|---|
| `GROQ_API_KEY` | yes | LLM for scripting |
| `SUPABASE_URL` / `SUPABASE_KEY` | yes | Job store |
| `R2_ACCOUNT_ID` / `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` / `R2_BUCKET` | yes | Where videos live |
| `R2_PUBLIC_BASE_URL` | no | Set for permanent URLs; otherwise presigned |
| `R2_RETENTION_DAYS` | no | Days before a video is auto-deleted, default 7 |
| `API_KEY` | no | Shared secret; **set it in production** |
| `PEXELS_API_KEY` / `PIXABAY_API_KEY` | no | Clip sources; falls back to Commons |

## Known gaps

These are deliberate, not oversights — they are the next things to build:

- **No real auth.** `user_id` is whatever the caller sends. `API_KEY` only stops
  strangers hitting the service; it does not stop one user reading another's
  jobs. Add real auth and Supabase RLS before this is public.
- **No quotas or rate limiting.** Rendering is the entire cost of this service,
  so an unmetered free tier gets expensive quickly.
- **No moderation** on user prompts or scripts.
- **Single worker.** One render at a time per process. `claim_next_job()` is not
  safe for multiple workers as written — see the note in `utils/jobs.py`.
- **Groq free tier is rate limited** per account, so concurrent users will see 429s.
