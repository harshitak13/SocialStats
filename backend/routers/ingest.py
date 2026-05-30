import asyncio

from fastapi import APIRouter, HTTPException

from models.schemas import IngestRequest, IngestResponse
from services.embeddings import embed_and_store
from services.instagram_service import get_instagram_data
from services.youtube_service import get_youtube_data


router = APIRouter(tags=["ingest"])


@router.post("/ingest", response_model=IngestResponse)
async def ingest_videos(payload: IngestRequest) -> IngestResponse:
    """Fetch two videos, embed their transcripts, and return comparison metadata."""
    print("SocialStats: fetching YouTube data...")
    print("SocialStats: fetching Instagram data...")

    try:
        video_a, video_b = await asyncio.gather(
            get_youtube_data(payload.youtube_url),
            get_instagram_data(payload.instagram_url),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"SocialStats could not fetch video data: {exc}",
        ) from exc

    print("SocialStats: embedding Video A...")
    print("SocialStats: embedding Video B...")

    try:
        chunks_a, chunks_b = await asyncio.gather(
            embed_and_store(video_a),
            embed_and_store(video_b),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="SocialStats could not embed transcripts. Check OPENAI_API_KEY and try again.",
        ) from exc

    print("SocialStats: ingest complete.")

    return IngestResponse(
        video_a=video_a,
        video_b=video_b,
        chunks_a=chunks_a,
        chunks_b=chunks_b,
        message=(
            f"SocialStats ingested {chunks_a} chunks for Video A "
            f"and {chunks_b} chunks for Video B."
        ),
    )
