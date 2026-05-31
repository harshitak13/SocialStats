from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.chat import router as chat_router
from routers.ingest import router as ingest_router


app = FastAPI(title="SocialStats API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://social-stats-one.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest_router, prefix="/api")
app.include_router(chat_router, prefix="/api")


@app.on_event("startup")
async def startup_event() -> None:
    """Log that the SocialStats API is ready to accept requests."""
    print("SocialStats API is running")


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Return the health status for the SocialStats API."""
    return {"status": "ok", "service": "SocialStats", "version": "1.0.0"}
