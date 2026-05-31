from collections.abc import AsyncGenerator
from os import getenv

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from models.schemas import ChatRequest
from services.rag_chain import get_rag_chain


router = APIRouter(tags=["chat"])


DEFAULT_ALLOWED_ORIGINS = {
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://social-stats-one.vercel.app",
    "https://social-stats-git-main-harshitak13s-projects.vercel.app",
    "https://social-stats-m2edxvmg7-harshitak13s-projects.vercel.app",
}


def _allowed_origins() -> set[str]:
    configured = {
        origin.strip().rstrip("/")
        for origin in getenv("ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    }
    return configured or DEFAULT_ALLOWED_ORIGINS


async def stream_response(question: str, session_id: str) -> AsyncGenerator[str, None]:
    """Stream SocialStats AI answer chunks as server-sent events."""
    try:
        chain = get_rag_chain(session_id)
        async for chunk in chain.astream({"question": question}):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as exc:
        yield f"data: [ERROR] {str(exc)}\n\n"


@router.post("/chat")
async def chat(payload: ChatRequest, request: Request) -> StreamingResponse:
    """Stream a RAG chat response for the requested SocialStats session."""
    response = StreamingResponse(
        stream_response(payload.question, payload.session_id),
        media_type="text/event-stream",
    )
    origin = (request.headers.get("origin") or "").rstrip("/")
    if origin in _allowed_origins():
        response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    return response
