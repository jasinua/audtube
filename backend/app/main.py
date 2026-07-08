"""FastAPI entrypoint for the audtube converter."""
import time
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from . import converter
from .validators import ValidationError, validate_format_and_quality, validate_url

app = FastAPI(title="audtube")

# Allow the Vite dev server (and any local origin) to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# TTL after which finished files are deleted (seconds).
FILE_TTL_SECONDS = 30 * 60


class ConvertRequest(BaseModel):
    url: str
    format: str = "mp3"
    quality: str = "192"


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/info")
def info(url: str = Query(...)):
    """Metadata preview shown as soon as the user pastes a link."""
    try:
        clean = validate_url(url)
        return converter.probe(clean)
    except ValidationError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@app.post("/api/convert")
def convert(req: ConvertRequest):
    """Synchronous convert: blocks until the file is ready, then returns a download path."""
    try:
        url = validate_url(req.url)
        fmt, quality = validate_format_and_quality(req.format, req.quality)
        # Probe first so we reject long/unavailable videos before downloading.
        converter.probe(url)
        result = converter.convert(url, fmt, quality)
    except ValidationError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    except Exception:  # noqa: BLE001 — never leak stack traces to the client.
        return JSONResponse(
            status_code=500,
            content={"error": "Something went wrong during conversion. Please try again."},
        )

    _cleanup_old_files()
    job_id = Path(result["filepath"]).stem
    return {
        "job_id": job_id,
        "filename": result["filename"],
        "title": result["title"],
        "download_url": f"/api/download/{job_id}",
    }


@app.get("/api/download/{job_id}")
def download(job_id: str, name: str = Query(default="download")):
    # job_id is a hex UUID stem; refuse anything else to prevent path traversal.
    if not job_id.isalnum():
        return JSONResponse(status_code=400, content={"error": "Invalid download id."})

    matches = list(converter.OUTPUT_DIR.glob(f"{job_id}.*"))
    if not matches:
        return JSONResponse(status_code=410, content={"error": "This file has expired."})

    filepath = matches[0]
    media_type = "audio/mpeg" if filepath.suffix == ".mp3" else "video/mp4"
    return FileResponse(path=filepath, media_type=media_type, filename=name)


def _cleanup_old_files():
    """Delete finished files older than the TTL. Cheap enough to run per request."""
    now = time.time()
    for f in converter.OUTPUT_DIR.glob("*"):
        try:
            if now - f.stat().st_mtime > FILE_TTL_SECONDS:
                f.unlink()
        except OSError:
            pass
