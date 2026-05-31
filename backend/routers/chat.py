from collections.abc import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from models.schemas import ChatRequest
from services.rag_chain import get_rag_chain


router = APIRouter(tags=["chat"])


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
    origin = request.headers.get("origin", "http://localhost:3000")
    allowed_origins = {
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://social-stats-one.vercel.app",
    }
    if origin not in allowed_origins:
        origin = "https://social-stats-one.vercel.app"
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    return response
