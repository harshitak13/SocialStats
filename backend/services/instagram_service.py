import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any

import yt_dlp
from dotenv import load_dotenv
from openai import OpenAI

from models.schemas import VideoMetadata


load_dotenv()


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
        # NOTE: Instagram often hides Reel duration from anonymous extraction.
        return "0:00"

    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _extract_hashtags(info: dict[str, Any]) -> list[str]:
    """Extract hashtags from Instagram metadata fields exposed by yt-dlp."""
    candidates = []
    candidates.extend(info.get("tags") or [])
    candidates.extend(info.get("hashtags") or [])

    for field in ("title", "description", "caption"):
        text = info.get(field) or ""
        if isinstance(text, str):
            candidates.extend(word for word in text.split() if word.startswith("#"))

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
        # NOTE: Instagram can hide play or view counts without authenticated API access.
        return 0.0
    return round((likes + comments) / views * 100, 2)


def _fetch_instagram_info(url: str) -> dict[str, Any]:
    """Extract Instagram Reel metadata with yt-dlp without downloading media."""
    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "ignoreerrors": False,
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        return ydl.extract_info(url, download=False) or {}


def _download_instagram_audio(url: str, output_dir: str) -> str:
    """Download Instagram Reel audio to a temporary file and return its path."""
    output_template = str(Path(output_dir) / "instagram_audio.%(ext)s")
    options = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([url])

    mp3_path = Path(output_dir) / "instagram_audio.mp3"
    if mp3_path.exists():
        return str(mp3_path)

    audio_files = [path for path in Path(output_dir).iterdir() if path.is_file()]
    return str(audio_files[0]) if audio_files else ""


def _transcribe_audio(audio_path: str) -> str:
    """Transcribe downloaded Reel audio with OpenAI Whisper."""
    if not audio_path or not os.getenv("OPENAI_API_KEY"):
        # NOTE: Whisper transcription needs OPENAI_API_KEY and a downloaded audio file.
        return ""

    client = OpenAI()
    with open(audio_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
        )
    return str(getattr(transcription, "text", "") or "")


async def _get_instagram_transcript(url: str) -> str:
    """Download Instagram Reel audio, transcribe it, and remove temporary files."""
    with tempfile.TemporaryDirectory(prefix="socialstats_instagram_") as temp_dir:
        audio_path = ""
        try:
            audio_path = await asyncio.to_thread(_download_instagram_audio, url, temp_dir)
            return await asyncio.to_thread(_transcribe_audio, audio_path)
        except Exception:
            # NOTE: Instagram can block downloads, and ffmpeg or Whisper may be unavailable.
            return ""
        finally:
            if audio_path:
                try:
                    Path(audio_path).unlink(missing_ok=True)
                except OSError:
                    pass


async def get_instagram_data(url: str) -> VideoMetadata:
    """Fetch Instagram Reel metadata and transcript data for SocialStats Video B."""
    try:
        info = await asyncio.to_thread(_fetch_instagram_info, url)
    except Exception:
        # NOTE: yt-dlp can fail when Instagram requires login or blocks anonymous extraction.
        info = {}

    views = _as_int(
        info.get("view_count")
        or info.get("play_count")
        or info.get("reel_play_count")
    )
    likes = _as_int(info.get("like_count"))
    comments = _as_int(info.get("comment_count"))
    transcript = await _get_instagram_transcript(url)

    return VideoMetadata(
        video_id="B",
        title=str(info.get("title") or info.get("description") or "Untitled Instagram Reel"),
        creator=str(info.get("uploader") or info.get("channel") or info.get("creator") or "Unknown creator"),
        views=views,
        likes=likes,
        comments=comments,
        # NOTE: Instagram blocks follower count without paid API access.
        follower_count=0,
        hashtags=_extract_hashtags(info),
        upload_date=str(info.get("upload_date") or ""),
        duration=_format_duration(info.get("duration")),
        engagement_rate=_calculate_engagement_rate(likes, comments, views),
        transcript=transcript,
    )
