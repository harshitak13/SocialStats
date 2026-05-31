import asyncio
import json
import os
import re
import tempfile
from contextlib import contextmanager
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import urlopen

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


def _extract_video_id(url: str) -> str:
    """Extract a YouTube video id from common YouTube URL formats."""
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower().replace("www.", "")
    if host == "youtu.be":
        return parsed.path.strip("/").split("/")[0]

    if host.endswith("youtube.com"):
        query_video_id = parse_qs(parsed.query).get("v", [""])[0]
        if query_video_id:
            return query_video_id

        path_parts = [part for part in parsed.path.split("/") if part]
        if len(path_parts) >= 2 and path_parts[0] in {"shorts", "embed", "live"}:
            return path_parts[1]

    if re.fullmatch(r"[\w-]{11}", url.strip()):
        return url.strip()
    return ""


def _parse_iso8601_duration(duration: str) -> int:
    """Convert a YouTube ISO-8601 duration string into seconds."""
    match = re.fullmatch(
        r"P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?",
        duration or "",
    )
    if not match:
        return 0
    days = _as_int(match.group("days"))
    hours = _as_int(match.group("hours"))
    minutes = _as_int(match.group("minutes"))
    seconds = _as_int(match.group("seconds"))
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


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
            "Add YOUTUBE_API_KEY to the backend for the official YouTube API fallback, "
            "or add YouTube cookies as YOUTUBE_COOKIES_CONTENT, then redeploy."
        )
    if "private video" in lower_message:
        return "This YouTube video is private or unavailable to the deployed server."
    if "video unavailable" in lower_message:
        return "This YouTube video is unavailable, deleted, region-blocked, or age-restricted."
    return f"YouTube metadata extraction failed: {message}"


def _fetch_json(endpoint: str, params: dict[str, str]) -> dict[str, Any]:
    """Fetch JSON from an HTTP endpoint using only the Python standard library."""
    url = f"{endpoint}?{urlencode(params)}"
    try:
        with urlopen(url, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise YouTubeExtractionError(
            f"YouTube Data API returned {exc.code}: {body[:300]}"
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise YouTubeExtractionError(f"YouTube Data API request failed: {exc}") from exc


def _fetch_youtube_info_from_api(url: str) -> dict[str, Any]:
    """Fetch YouTube metadata and stats with the official YouTube Data API."""
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise YouTubeExtractionError("YOUTUBE_API_KEY is not configured.")

    video_id = _extract_video_id(url)
    if not video_id:
        raise YouTubeExtractionError("Could not find a YouTube video id in the URL.")

    video_payload = _fetch_json(
        "https://www.googleapis.com/youtube/v3/videos",
        {
            "part": "snippet,statistics,contentDetails",
            "id": video_id,
            "key": api_key,
        },
    )
    items = video_payload.get("items") or []
    if not items:
        raise YouTubeExtractionError(
            "The YouTube Data API could not find this video. It may be private, deleted, or restricted."
        )

    item = items[0]
    snippet = item.get("snippet") or {}
    statistics = item.get("statistics") or {}
    content_details = item.get("contentDetails") or {}
    channel_id = snippet.get("channelId") or ""
    follower_count = 0

    if channel_id:
        channel_payload = _fetch_json(
            "https://www.googleapis.com/youtube/v3/channels",
            {
                "part": "statistics",
                "id": channel_id,
                "key": api_key,
            },
        )
        channel_items = channel_payload.get("items") or []
        if channel_items:
            follower_count = _as_int(
                (channel_items[0].get("statistics") or {}).get("subscriberCount")
            )

    return {
        "id": video_id,
        "title": snippet.get("title") or "",
        "uploader": snippet.get("channelTitle") or "",
        "channel": snippet.get("channelTitle") or "",
        "view_count": statistics.get("viewCount"),
        "like_count": statistics.get("likeCount"),
        "comment_count": statistics.get("commentCount"),
        "channel_follower_count": follower_count,
        "tags": snippet.get("tags") or [],
        "upload_date": str(snippet.get("publishedAt") or "")[:10].replace("-", ""),
        "duration": _parse_iso8601_duration(content_details.get("duration") or ""),
    }


def _fetch_youtube_info(url: str) -> dict[str, Any]:
    """Extract YouTube metadata with yt-dlp without downloading media."""
    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "ignoreerrors": False,
        "noplaylist": True,
        "retries": 2,
        "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
    }
    extraction_error = None
    with _youtube_cookiefile() as cookiefile:
        if cookiefile:
            options["cookiefile"] = cookiefile
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False) or {}
        except Exception as exc:
            extraction_error = exc
            info = {}

    if not info.get("id"):
        try:
            return _fetch_youtube_info_from_api(url)
        except YouTubeExtractionError as api_error:
            if extraction_error:
                raise YouTubeExtractionError(_format_youtube_error(extraction_error)) from api_error
            raise YouTubeExtractionError(
                "YouTube returned empty metadata. Add YOUTUBE_API_KEY to the backend "
                "for the official YouTube API fallback, or add YOUTUBE_COOKIES_CONTENT, then redeploy."
            ) from api_error
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
