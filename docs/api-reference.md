# API Reference

## Base URL
```
http://localhost:7860
```

## Authentication
When `API_KEY` is set on the server, all endpoints except `/health` require the header:
```
X-API-Key: <your-api-key>
```

---

## Endpoints

### `GET /health`

Liveness check.

**Response:**
```json
{
  "status": "healthy",
  "storage_configured": true
}
```

---

### `GET /topics/suggestions`

Get AI-generated topic ideas for the video picker.

**Query Parameters:**
| Param | Type | Default | Description |
|---|---|---|---|
| `count` | int | 6 | Number of suggestions (1-12) |
| `category` | string | — | Filter by category |

**Categories:** `software_engineering`, `ai`, `cybersecurity`, `startups`, `productivity`, `finance`, `marketing`, `design`, `devops`, `data_science`, `mobile_dev`, `web_dev`, `blockchain`, `cloud_computing`, `gaming`

**Response:**
```json
{
  "topics": [
    {
      "topic": "How AI is changing code review",
      "category": "ai",
      "hook": "What if your next PR review was done by an AI?"
    }
  ]
}
```

---

### `POST /jobs`

Queue a new video generation job.

**Request Body:**
```json
{
  "user_id": "device-uuid-string",
  "prompt": "Tell me about the future of web development",
  "script": null
}
```

> Either `prompt` or `script` must be provided (not both empty, not both set).

**Response (202 Accepted):**
```json
{
  "id": "job-uuid",
  "status": "queued",
  "stage": "queued"
}
```

**Errors:**
- `400` — Neither prompt nor script provided
- `500` — R2 storage not configured

---

### `GET /jobs/{job_id}`

Poll a job's progress.

**Path Parameters:**
| Param | Type | Description |
|---|---|---|
| `job_id` | uuid | The job ID |

**Query Parameters:**
| Param | Type | Required |
|---|---|---|
| `user_id` | string | Yes |

**Response:**
```json
{
  "id": "job-uuid",
  "status": "completed",
  "stage": "done",
  "title": "How AI is changing code review",
  "video_url": "https://your-bucket.r2.dev/video.mp4",
  "error": null,
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Stages (in order):**
`queued` → `scripting` → `clips` → `voice` → `rendering` → `uploading` → `done`

**Statuses:** `queued` | `processing` | `completed` | `failed`

---

### `GET /jobs`

List all jobs for a user.

**Query Parameters:**
| Param | Type | Default | Description |
|---|---|---|---|
| `user_id` | string | — | Required. Device UUID |
| `limit` | int | 50 | Max results (1-100) |

**Response:**
```json
{
  "jobs": [
    {
      "id": "job-uuid",
      "status": "completed",
      "stage": "done",
      "title": "How AI is changing code review",
      "video_url": "...",
      "error": null,
      "created_at": "2025-01-15T10:30:00Z"
    }
  ]
}
```

---

### `DELETE /jobs/{job_id}`

Delete a job from library, SQLite, and R2.

**Path Parameters:**
| Param | Type | Description |
|---|---|---|
| `job_id` | uuid | The job ID |

**Query Parameters:**
| Param | Type | Required |
|---|---|---|
| `user_id` | string | Yes |

**Response:**
```json
{
  "success": true
}
```

---

## Error Responses

All errors follow this shape:
```json
{
  "detail": "Error message here"
}
```
