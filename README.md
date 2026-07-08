# audtube

A minimal YouTube → MP3 / MP4 converter. Paste a link, pick a format, download.

> **Personal use only.** Downloading YouTube content may violate YouTube's Terms
> of Service and copyright law. Use it with content you own or that is licensed
> for reuse. Keep this app private.

## Stack

- **Frontend:** React + Vite + TypeScript + Tailwind
- **Backend:** FastAPI (Python) + yt-dlp + ffmpeg (synchronous, no queue)

## Prerequisites (macOS)

```bash
brew install python@3.12 ffmpeg deno
```

- **Python 3.12+** is required — yt-dlp has dropped 3.9, and the system Python's
  old TLS stack breaks YouTube extraction.
- **deno** gives yt-dlp a JS runtime to solve YouTube's signature challenge.
- **ffmpeg** does the audio/video conversion.

## Setup

```bash
# Backend
cd backend
python3.12 -m venv venv
./venv/bin/pip install -U pip
./venv/bin/pip install -U --pre "yt-dlp[default]"
./venv/bin/pip install fastapi "uvicorn[standard]" python-multipart

# Frontend
cd ../frontend
npm install
```

## Run (two terminals)

```bash
# Terminal 1 — backend (http://localhost:8000)
cd backend && ./run.sh

# Terminal 2 — frontend (http://localhost:5173)
cd frontend && npm run dev
```

Open http://localhost:5173.

### Use it from your phone (same WiFi)

The dev server prints a **Network** URL like `http://192.168.x.x:5173/`.
Open that on your phone (both devices on the same WiFi). API calls are proxied
to the backend automatically.

## Keeping it working

YouTube changes constantly and **breaks yt-dlp**. When conversions start failing,
update it:

```bash
cd backend && ./venv/bin/pip install -U --pre "yt-dlp[default]"
```

## Notes / limits

- Max video length: 2 hours. Playlists are rejected.
- Converted files auto-delete after 30 minutes.
- Single video at a time; no job queue (conversions are synchronous).
