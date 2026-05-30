import asyncio
from typing import Any

import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

from models.schemas import VideoMetadata


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


def _fetch_youtube_info(url: str) -> dict[str, Any]:
    """Extract YouTube metadata with yt-dlp without downloading media."""
    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "ignoreerrors": False,
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        return ydl.extract_info(url, download=False) or {}


def _entry_text(entry: Any) -> str:
    """Read transcript text from either dict-like or object-like entries."""
    if isinstance(entry, dict):
        return str(entry.get("text") or "").strip()
    return str(getattr(entry, "text", "") or "").strip()


def _fetch_youtube_transcript(source_video_id: str) -> str:
    """Fetch and join the full YouTube transcript text for a video."""
    try:
        transcript_entries = YouTubeTranscriptApi.get_transcript(source_video_id)
    except AttributeError:
        transcript_entries = YouTubeTranscriptApi().fetch(source_video_id)

    return " ".join(
        text for text in (_entry_text(entry) for entry in transcript_entries) if text
    )


async def get_youtube_data(url: str) -> VideoMetadata:
    """Fetch YouTube metadata and transcript data for SocialStats Video A."""
    try:
        info = await asyncio.to_thread(_fetch_youtube_info, url)
    except Exception:
        # NOTE: yt-dlp can fail for private, deleted, geo-blocked, or login-gated videos.
        info = {}

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
