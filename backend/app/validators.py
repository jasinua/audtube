"""URL and input validation for the converter."""
import re

# Accept standard watch links, short youtu.be links, and Shorts.
_YOUTUBE_PATTERNS = [
    re.compile(r"^https?://(www\.)?youtube\.com/watch\?[^ ]*\bv=[\w-]{11}", re.I),
    re.compile(r"^https?://(www\.)?youtube\.com/shorts/[\w-]{11}", re.I),
    re.compile(r"^https?://youtu\.be/[\w-]{11}", re.I),
    re.compile(r"^https?://(m|music)\.youtube\.com/watch\?[^ ]*\bv=[\w-]{11}", re.I),
]

# Reject playlist URLs for v1 (a single video only).
_PLAYLIST_RE = re.compile(r"[?&]list=", re.I)

MAX_DURATION_SECONDS = 2 * 60 * 60  # 2 hours

VALID_MP3_QUALITIES = {"128", "192", "320"}
VALID_MP4_QUALITIES = {"360", "720", "1080"}


class ValidationError(Exception):
    """Raised when user input fails validation."""


def validate_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        raise ValidationError("Please paste a YouTube link.")
    if _PLAYLIST_RE.search(url):
        raise ValidationError("Playlists aren't supported — paste a single video link.")
    if not any(p.match(url) for p in _YOUTUBE_PATTERNS):
        raise ValidationError("That doesn't look like a valid YouTube video link.")
    return url


def validate_format_and_quality(fmt: str, quality: str) -> tuple[str, str]:
    fmt = (fmt or "").lower().strip()
    quality = str(quality or "").strip()
    if fmt == "mp3":
        if quality not in VALID_MP3_QUALITIES:
            raise ValidationError("Invalid MP3 quality. Choose 128, 192, or 320 kbps.")
    elif fmt == "mp4":
        if quality not in VALID_MP4_QUALITIES:
            raise ValidationError("Invalid MP4 quality. Choose 360, 720, or 1080p.")
    else:
        raise ValidationError("Format must be mp3 or mp4.")
    return fmt, quality


def sanitize_filename(name: str) -> str:
    """Make a video title safe to use as a download filename."""
    name = (name or "download").strip()
    # Strip characters that break Content-Disposition or filesystems.
    name = re.sub(r'[\\/:*?"<>|\r\n\t]', "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:120] or "download"
