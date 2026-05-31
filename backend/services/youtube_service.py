import asyncio
import os
import tempfile
from contextlib import contextmanager
from typing import Any

import yt_dlp
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi

from models.schemas import VideoMetadata


load_dotenv()


class YouTubeExtractionError(RuntimeError):
    """Raised when SocialStats cannot extract YouTube metadata."""


def _as_int(value: Any) -> int:
    """Convert a metadata value to an integer with a safe zero default."""
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _format_duration(seconds: Any) -> str:
    """Format a duration in seconds as M:SS or H:MM:SS."""
    total_seconds = _as_int(seconds)
    if total_seconds <= 0:
        # NOTE: YouTube may omit duration for private, deleted, or restricted videos.
        return "0:00"

    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _extract_hashtags(info: dict[str, Any]) -> list[str]:
    """Extract hashtags from yt-dlp tag and title fields."""
    candidates = []
    candidates.extend(info.get("tags") or [])

    title = info.get("title") or ""
    if isinstance(title, str):
        candidates.extend(word for word in title.split() if word.startswith("#"))

    hashtags = []
    for tag in candidates:
        if not isinstance(tag, str):
            continue
        cleaned = tag.strip().rstrip(".,;:")
        if not cleaned:
            continue
        hashtags.append(cleaned if cleaned.startswith("#") else f"#{cleaned}")

    return list(dict.fromkeys(hashtags))


def _calculate_engagement_rate(likes: int, comments: int, views: int) -> float:
    """Calculate engagement rate as a percentage rounded to two decimals."""
    if views <= 0:
        # NOTE: View counts can be unavailable for private or newly published videos.
        return 0.0
    return round((likes + comments) / views * 100, 2)


@contextmanager
def _youtube_cookiefile():
    """Yield a yt-dlp cookie file path from env vars when one is configured."""
    cookie_file = os.getenv("YOUTUBE_COOKIES_FILE") or os.getenv("YOUTUBE_COOKIE_FILE")
    if cookie_file:
        yield cookie_file
        return

    cookies_content = os.getenv("YOUTUBE_COOKIES_CONTENT") or os.getenv("YOUTUBE_COOKIES")
    if not cookies_content:
        yield None
        return

    temp_path = ""
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            delete=False,
            suffix=".txt",
        ) as cookie_file:
            cookie_file.write(cookies_content.replace("\\n", "\n"))
            temp_path = cookie_file.name
        yield temp_path
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def _format_youtube_error(exc: Exception) -> str:
    """Return a user-facing explanation for common YouTube extraction failures."""
    message = str(exc)
    lower_message = message.lower()
    if "sign in to confirm" in lower_message or "not a bot" in lower_message:
        return (
            "YouTube blocked the deployed server as an automated request. "
            "Add YouTube cookies to the backend as YOUTUBE_COOKIES_CONTENT and redeploy."
        )
    if "private video" in lower_message:
        return "This YouTube video is private or unavailable to the deployed server."
    if "video unavailable" in lower_message:
        return "This YouTube video is unavailable, deleted, region-blocked, or age-restricted."
    return f"YouTube metadata extraction failed: {message}"


def _fetch_youtube_info(url: str) -> dict[str, Any]:
    """Extract YouTube metadata with yt-dlp without downloading media."""
    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "ignoreerrors": False,
        "noplaylist": True,
        "retries": 2,
    }
    with _youtube_cookiefile() as cookiefile:
        if cookiefile:
            options["cookiefile"] = cookiefile
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False) or {}
        except Exception as exc:
            raise YouTubeExtractionError(_format_youtube_error(exc)) from exc

    if not info.get("id"):
        raise YouTubeExtractionError(
            "YouTube returned empty metadata. If this only happens on Render, add "
            "YOUTUBE_COOKIES_CONTENT to the backend environment and redeploy."
        )
    return info


def _fetch_youtube_transcript(source_video_id: str) -> str:
    """Fetch and join the full YouTube transcript text for a video."""
    try:
        transcript_entries = YouTubeTranscriptApi.get_transcript(source_video_id)
    except AttributeError:
        transcript_entries = YouTubeTranscriptApi().fetch(source_video_id)

    return " ".join(
        text for text in (_entry_text(entry) for entry in transcript_entries) if text
    )


def _entry_text(entry: Any) -> str:
    """Read transcript text from either dict-like or object-like entries."""
    if isinstance(entry, dict):
        return str(entry.get("text") or "").strip()
    return str(getattr(entry, "text", "") or "").strip()


async def get_youtube_data(url: str) -> VideoMetadata:
    """Fetch YouTube metadata and transcript data for SocialStats Video A."""
    info = await asyncio.to_thread(_fetch_youtube_info, url)

    views = _as_int(info.get("view_count"))
    likes = _as_int(info.get("like_count"))
    comments = _as_int(info.get("comment_count"))
    source_video_id = str(info.get("id") or "")

    transcript = ""
    if source_video_id:
        try:
            transcript = await asyncio.to_thread(
                _fetch_youtube_transcript,
                source_video_id,
            )
        except Exception:
            # NOTE: Some YouTube videos have disabled, missing, or language-restricted transcripts.
            transcript = ""

    return VideoMetadata(
        video_id="A",
        title=str(info.get("title") or "Untitled YouTube video"),
        creator=str(info.get("uploader") or info.get("channel") or "Unknown creator"),
        views=views,
        likes=likes,
        comments=comments,
        follower_count=_as_int(
            info.get("channel_follower_count")
            or info.get("channel_subscriber_count")
            or info.get("uploader_subscriber_count")
        ),
        hashtags=_extract_hashtags(info),
        upload_date=str(info.get("upload_date") or ""),
        duration=_format_duration(info.get("duration")),
        engagement_rate=_calculate_engagement_rate(likes, comments, views),
        transcript=transcript,
    )
