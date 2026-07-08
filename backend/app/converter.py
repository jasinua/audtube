"""yt-dlp + ffmpeg conversion logic (synchronous, no queue)."""
import glob
import os
import uuid
from pathlib import Path

import yt_dlp

from .validators import (
    MAX_DURATION_SECONDS,
    ValidationError,
    sanitize_filename,
)

# Where finished files live until the TTL cleanup removes them.
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/tmp/audtube"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Path to a Netscape-format cookies.txt exported from a logged-in YouTube
# session. Required on datacenter hosts (Render) where YouTube demands sign-in.
# Unset locally (residential IP usually works without it).
COOKIES_FILE = os.environ.get("YOUTUBE_COOKIES_FILE", "").strip()


def _base_opts() -> dict:
    """Common yt-dlp options, including cookies when configured."""
    opts: dict = {"quiet": True, "no_warnings": True, "noplaylist": True}
    if COOKIES_FILE and os.path.exists(COOKIES_FILE):
        opts["cookiefile"] = COOKIES_FILE
    return opts


def probe(url: str) -> dict:
    """Fetch metadata without downloading, for instant UI feedback."""
    opts = {**_base_opts(), "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
        except yt_dlp.utils.DownloadError as e:
            raise ValidationError(_friendly_error(str(e)))

    duration = info.get("duration") or 0
    if duration > MAX_DURATION_SECONDS:
        raise ValidationError("That video is longer than 2 hours — too long to convert.")

    return {
        "title": info.get("title") or "Unknown title",
        "thumbnail": info.get("thumbnail"),
        "duration": duration,
        "channel": info.get("uploader") or info.get("channel"),
    }


def convert(url: str, fmt: str, quality: str) -> dict:
    """Download and convert. Returns {filepath, filename, title}. Blocks until done."""
    job_id = uuid.uuid4().hex
    out_stem = str(OUTPUT_DIR / job_id)

    if fmt == "mp3":
        opts = {
            **_base_opts(),
            "format": "bestaudio/best",
            "outtmpl": out_stem + ".%(ext)s",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": quality,
                },
                {"key": "FFmpegMetadata"},
            ],
        }
        ext = "mp3"
    else:  # mp4
        opts = {
            **_base_opts(),
            "format": (
                f"bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/"
                f"bestvideo[height<={quality}]+bestaudio/"
                f"best[height<={quality}]"
            ),
            "merge_output_format": "mp4",
            "outtmpl": out_stem + ".%(ext)s",
        }
        ext = "mp4"

    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            info = ydl.extract_info(url, download=True)
        except yt_dlp.utils.DownloadError as e:
            raise ValidationError(_friendly_error(str(e)))

    filepath = out_stem + "." + ext
    if not os.path.exists(filepath):
        # Fall back to whatever the postprocessor actually produced.
        matches = glob.glob(out_stem + ".*")
        if not matches:
            raise ValidationError("Conversion failed — no output file was produced.")
        filepath = matches[0]
        ext = filepath.rsplit(".", 1)[-1]

    title = sanitize_filename(info.get("title") or "download")
    return {
        "filepath": filepath,
        "filename": f"{title}.{ext}",
        "title": info.get("title") or "download",
    }


def _friendly_error(raw: str) -> str:
    low = raw.lower()
    if "private" in low:
        return "This video is private."
    if "age" in low and "restrict" in low:
        return "This video is age-restricted and can't be converted."
    if "unavailable" in low or "removed" in low or "not available" in low:
        return "This video is unavailable or has been removed."
    if "sign in" in low or "bot" in low:
        return "YouTube is asking for sign-in — try a different video."
    return "Couldn't process this video. Please check the link and try again."
