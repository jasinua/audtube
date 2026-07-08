#!/usr/bin/env bash
# Start the audtube backend. Ensures ffmpeg + deno (Homebrew) are on PATH.
set -e
cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:$PATH"
export OUTPUT_DIR="${OUTPUT_DIR:-/tmp/audtube}"
exec ./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
