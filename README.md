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

## Deployment (Render backend + Netlify frontend)

The backend needs ffmpeg + a real server, so it can't go on Netlify. Backend →
Render (Docker), frontend → Netlify.

### 1. Push this repo to GitHub

### 2. Backend on Render
1. Render dashboard → **New → Blueprint** → pick this repo. It reads `render.yaml`.
2. Render builds `backend/Dockerfile` (ffmpeg + deno + yt-dlp baked in).
3. After deploy, open the service → **Environment** → copy the auto-generated
   **`API_SECRET`** value (you'll need it for Netlify).
4. Note the service URL, e.g. `https://audtube-backend.onrender.com`.

> Free instances sleep after ~15 min idle; the first request then takes ~30s to wake.

### 3. Frontend on Netlify
1. Netlify → **Add new site → Import from Git** → pick this repo.
   `frontend/netlify.toml` sets the base dir and build command.
2. **Site settings → Environment variables**, add:
   - `VITE_API_URL` = your Render URL (e.g. `https://audtube-backend.onrender.com`)
   - `VITE_API_KEY` = the `API_SECRET` value from Render
3. Deploy. Note your Netlify URL, e.g. `https://audtube.netlify.app`.

### 4. Lock CORS to your frontend
Back in Render → the service's **Environment** → set
`ALLOWED_ORIGIN` = your Netlify URL → save (redeploys).

Now open the Netlify URL on your phone — works from anywhere, Mac off. Add it to
your home screen for an app-like icon.

## Notes / limits

- Max video length: 2 hours. Playlists are rejected.
- Converted files auto-delete after 30 minutes.
- Single video at a time; no job queue (conversions are synchronous).
