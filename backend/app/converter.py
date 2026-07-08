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

# yt-dlp writes refreshed cookies back to the file, but Render Secret Files are
# mounted read-only. Copy the source to a writable path and use that copy.
_WRITABLE_COOKIES: str | None = None


def _get_cookies_path() -> str | None:
    """Return a writable copy of the cookies file, or None if not configured."""
    global _WRITABLE_COOKIES
    if not COOKIES_FILE or not os.path.exists(COOKIES_FILE):
        return None
    if _WRITABLE_COOKIES and os.path.exists(_WRITABLE_COOKIES):
        return _WRITABLE_COOKIES
    import shutil

    dest = str(OUTPUT_DIR / "cookies.txt")
    shutil.copyfile(COOKIES_FILE, dest)
    _WRITABLE_COOKIES = dest
    return dest


# Player clients to try, in order. The "tv"/"mweb"/"web_embedded" clients can
# sometimes bypass YouTube's datacenter-IP bot check when the default "web"
# client is rejected. Overridable via YOUTUBE_PLAYER_CLIENTS (comma-separated).
_DEFAULT_CLIENTS = ["tv", "mweb", "web_safari", "web"]
PLAYER_CLIENTS = [
    c.strip()
    for c in os.environ.get("YOUTUBE_PLAYER_CLIENTS", "").split(",")
    if c.strip()
] or _DEFAULT_CLIENTS


def _base_opts(client: str | None = None) -> dict:
    """Common yt-dlp options, including cookies + a specific player client."""
    opts: dict = {"quiet": True, "no_warnings": True, "noplaylist": True}
    cookies = _get_cookies_path()
    if cookies:
        opts["cookiefile"] = cookies
    if client:
        opts["extractor_args"] = {"youtube": {"player_client": [client]}}
    return opts


def _extract(url: str, extra_opts: dict, download: bool):
    """Try each player client in turn; return (info, working_client).

    YouTube may reject some clients (esp. from datacenter IPs) but accept
    others, so we fall through the list until one succeeds.
    """
    last_err: Exception | None = None
    for client in PLAYER_CLIENTS:
        opts = {**_base_opts(client), **extra_opts}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=download)
            return info, client
        except Exception as e:  # noqa: BLE001 — remember and try the next client.
            last_err = e
            continue
    raise ValidationError(_friendly_error(str(last_err) if last_err else ""))


def probe(url: str) -> dict:
    """Fetch metadata without downloading, for instant UI feedback."""
    info, _ = _extract(url, {"skip_download": True}, download=False)

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
        extra = {
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
        extra = {
            "format": (
                f"bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/"
                f"bestvideo[height<={quality}]+bestaudio/"
                f"best[height<={quality}]"
            ),
            "merge_output_format": "mp4",
            "outtmpl": out_stem + ".%(ext)s",
        }
        ext = "mp4"

    info, _ = _extract(url, extra, download=True)

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
