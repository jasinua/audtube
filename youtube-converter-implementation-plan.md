# Implementation Plan: YouTube → MP3/MP4 Converter Website

## 1. Project Overview

A single-purpose web app where a user pastes a YouTube link, picks a format (MP3 audio or MP4 video) and quality, and downloads the converted file. The UI should be minimal: one input, one button, a clean result card. No accounts, no clutter.

**Goals**
- Paste link → convert → download in under 3 clicks
- Fast perceived speed (progress feedback, no dead waiting screens)
- Clean, modern, mobile-first UI
- Handle concurrent conversions reliably

**Important legal note:** Downloading YouTube content generally violates YouTube's Terms of Service, and distributing copyrighted material without permission can infringe copyright law. If this is a real public product, plan for takedown handling, restrict usage to content the user owns / Creative Commons material, and consult a lawyer. For a personal/learning project, keep it private.

---

## 2. Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | React (Vite) + Tailwind CSS | Fast dev, easy clean UI |
| Backend | Node.js (Express) or Python (FastAPI) | FastAPI pairs naturally with yt-dlp (Python) |
| Downloader | `yt-dlp` | Actively maintained, handles formats/streams |
| Converter | `ffmpeg` | Audio extraction, transcoding, metadata |
| Job queue | Redis + worker process (BullMQ / Celery / RQ) | Conversions are slow; don't block HTTP requests |
| Storage | Local temp disk (auto-cleanup) or S3-compatible bucket | Files are short-lived |
| Deployment | Docker + VPS (Hetzner/DigitalOcean) | ffmpeg/yt-dlp need a real server, not serverless |

Recommended: **FastAPI + yt-dlp + ffmpeg + Redis/RQ**, React frontend.

---

## 3. System Architecture

```
[Browser]
   │  POST /api/convert  { url, format, quality }
   ▼
[API Server]  ── validates URL, creates job ──▶ [Redis Queue]
   │                                                 │
   │  job_id returned                                ▼
   │                                          [Worker Process]
   │                                          yt-dlp → ffmpeg
   │                                                 │
   │  GET /api/status/{job_id}  (poll or SSE)        ▼
   │◀──────────────────────────────  [Temp Storage /files]
   ▼
GET /api/download/{job_id}  → streamed file → auto-delete after N minutes
```

**Flow**
1. User pastes URL → frontend calls `POST /api/convert`
2. API validates the URL (regex + yt-dlp metadata probe), enqueues a job, returns `job_id` plus video title/thumbnail/duration for instant UI feedback
3. Worker downloads best matching stream with yt-dlp:
   - MP3: download bestaudio → ffmpeg → MP3 (128/192/320 kbps), embed title + thumbnail as cover art
   - MP4: download best video+audio muxed at chosen resolution (360p/720p/1080p)
4. Frontend polls `GET /api/status/{job_id}` (or listens via Server-Sent Events) and shows progress
5. On completion, UI shows a download button → `GET /api/download/{job_id}` streams the file
6. Cleanup job deletes files older than ~30 minutes

---

## 4. API Design

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/convert` | Body: `{ url, format: "mp3"\|"mp4", quality }` → `{ job_id, title, thumbnail, duration }` |
| GET | `/api/status/{job_id}` | `{ state: queued\|downloading\|converting\|done\|error, progress: 0-100 }` |
| GET | `/api/download/{job_id}` | Streams file with `Content-Disposition: attachment; filename="Title.mp3"` |
| GET | `/api/info?url=` | (Optional) metadata preview before converting |

**Validation rules**
- Accept only `youtube.com/watch`, `youtu.be/`, `youtube.com/shorts/` URLs
- Reject playlists (or cap at 1 video for v1)
- Cap video length (e.g., max 2 hours) to protect the server
- Sanitize filenames from video titles

---

## 5. UI / UX Plan

**Design principles:** one screen, one job. Lots of whitespace, a single accent color, system font stack or Inter, subtle shadows, rounded corners. Dark mode optional (v2).

**Layout (single page)**

```
┌──────────────────────────────────────────────┐
│              🎵  TubeGrab (logo)             │
│                                              │
│     Paste a YouTube link to get started     │
│  ┌────────────────────────────┬──────────┐  │
│  │ https://youtube.com/...    │ Convert  │  │
│  └────────────────────────────┴──────────┘  │
│         ( MP3 ● )   ( MP4 ○ )   quality ▾   │
│                                              │
│  ┌ Result card ───────────────────────────┐ │
│  │ [thumb]  Video Title                   │ │
│  │          03:45 · 320kbps MP3           │ │
│  │          ▓▓▓▓▓▓▓░░░ 68% converting…    │ │
│  │          [ ⬇ Download ]                │ │
│  └────────────────────────────────────────┘ │
│                                              │
│         footer: FAQ · Terms · Contact        │
└──────────────────────────────────────────────┘
```

**Interaction details**
- Auto-detect a YouTube URL on paste and fetch metadata immediately (title + thumbnail appear before the user clicks Convert — feels fast)
- Format toggle: MP3 / MP4 as segmented control; quality dropdown adapts (MP3: 128/192/320 kbps, MP4: 360p/720p/1080p)
- Progress states: `Fetching info → Downloading → Converting → Ready`, with an animated progress bar
- Errors shown inline in the card ("Video unavailable", "Too long", "Invalid link") — never raw stack traces
- Fully responsive; the input stacks above the button on mobile
- Accessibility: proper labels, focus states, keyboard-friendly

---

## 6. Backend Implementation Details

**Worker pseudocode (MP3 path)**

```python
def convert_job(job_id, url, fmt, quality):
    info = yt_dlp.extract_info(url, download=False)
    if info["duration"] > MAX_DURATION: fail("Video too long")

    if fmt == "mp3":
        opts = {
            "format": "bestaudio/best",
            "outtmpl": f"/tmp/{job_id}.%(ext)s",
            "postprocessors": [
                {"key": "FFmpegExtractAudio",
                 "preferredcodec": "mp3",
                 "preferredquality": quality},   # e.g. "320"
                {"key": "EmbedThumbnail"},
                {"key": "FFmpegMetadata"},
            ],
            "progress_hooks": [update_progress(job_id)],
        }
    else:  # mp4
        opts = {
            "format": f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]",
            "merge_output_format": "mp4",
            "outtmpl": f"/tmp/{job_id}.%(ext)s",
            "progress_hooks": [update_progress(job_id)],
        }

    yt_dlp.YoutubeDL(opts).download([url])
    mark_done(job_id, filepath)
```

**Operational concerns**
- Keep yt-dlp auto-updated (it breaks when YouTube changes) — cron `yt-dlp -U` or pin + weekly bump
- Limit concurrent worker jobs (2–4 per CPU core; ffmpeg is CPU-heavy)
- Per-IP rate limiting (e.g., 5 conversions / 10 min) + optional CAPTCHA if abused
- Disk watchdog: refuse new jobs if free space < threshold
- Cleanup cron: delete `/tmp` outputs older than 30 min
- Structured logging + basic metrics (jobs/hour, failure rate)

---

## 7. Security & Abuse Prevention

- Strict URL allowlist (YouTube domains only) — prevents SSRF
- Never shell-interpolate user input; use yt-dlp's Python API or arg arrays
- Random, unguessable `job_id` (UUIDv4); download endpoint checks job ownership via cookie/session token
- File size cap + duration cap
- Rate limiting + basic bot protection
- Serve behind HTTPS (Caddy or nginx + Let's Encrypt)

---

## 8. Project Structure

```
tubegrab/
├── frontend/
│   ├── src/
│   │   ├── components/ (UrlInput, FormatToggle, ResultCard, ProgressBar)
│   │   ├── hooks/useConversion.ts
│   │   └── App.tsx
│   └── index.html
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI routes
│   │   ├── jobs.py          # queue + worker logic
│   │   ├── validators.py    # URL/duration checks
│   │   └── cleanup.py
│   └── requirements.txt
├── docker-compose.yml        # api + worker + redis + nginx
└── README.md
```

---

## 9. Milestones & Timeline

| Phase | Scope | Est. |
|---|---|---|
| **1. Core backend** | FastAPI, yt-dlp MP3 conversion, sync (no queue), download endpoint | 2–3 days |
| **2. Job queue** | Redis + worker, status polling, progress hooks, cleanup | 2 days |
| **3. Frontend MVP** | Input, format toggle, result card, polling, download | 2–3 days |
| **4. MP4 support** | Quality selection, muxing, larger-file streaming | 1–2 days |
| **5. Polish** | Metadata preview on paste, error states, mobile, favicon/branding | 2 days |
| **6. Hardening** | Rate limiting, caps, HTTPS, Docker deploy, monitoring | 2 days |
| **7. Nice-to-haves (v2)** | Dark mode, SSE progress, trim start/end, batch/playlist, PWA | ongoing |

**Total MVP: ~10–14 days** of focused work.

---

## 10. Testing Checklist

- ✅ Valid watch / youtu.be / shorts URLs convert correctly
- ✅ Playlist URL rejected gracefully
- ✅ Private/deleted/age-restricted videos → clean error message
- ✅ Very long video → duration cap error
- ✅ Concurrent jobs (10+) don't crash the worker
- ✅ File deleted after TTL; expired download link returns 410
- ✅ Filename with emojis/special chars downloads safely
- ✅ Mobile Safari + Chrome download behavior verified

---

## 11. Deployment

1. Dockerize: `api`, `worker`, `redis`, `nginx` services in docker-compose
2. VPS with ≥2 vCPU / 4 GB RAM / 40 GB disk
3. Caddy or nginx reverse proxy with automatic HTTPS
4. Cron: yt-dlp update + temp-file cleanup
5. Uptime monitoring (UptimeRobot) + error alerts

---

## 12. Risks

| Risk | Mitigation |
|---|---|
| YouTube blocks/breaks extraction | Auto-update yt-dlp; graceful "temporarily unavailable" error |
| Legal/ToS exposure | Terms page, DMCA contact, restrict to permitted content, or keep private |
| Server overload | Queue + concurrency limits + rate limiting + duration caps |
| Disk fill-up | TTL cleanup + free-space guard |
