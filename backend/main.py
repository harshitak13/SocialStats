import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.chat import router as chat_router
from routers.ingest import router as ingest_router


app = FastAPI(title="SocialStats API", version="1.0.0")

DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://social-stats-one.vercel.app",
    "https://social-stats-git-main-harshitak13s-projects.vercel.app",
    "https://social-stats-m2edxvmg7-harshitak13s-projects.vercel.app",
]

allowed_origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
] or DEFAULT_ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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
