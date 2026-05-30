from pydantic import BaseModel


class VideoMetadata(BaseModel):
    video_id: str
    title: str
    creator: str
    views: int
    likes: int
    comments: int
    follower_count: int
    hashtags: list[str]
    upload_date: str
    duration: str
    engagement_rate: float
    transcript: str


class IngestRequest(BaseModel):
    youtube_url: str
    instagram_url: str


class IngestResponse(BaseModel):
    video_a: VideoMetadata
    video_b: VideoMetadata
    chunks_a: int
    chunks_b: int
    message: str


class ChatRequest(BaseModel):
    question: str
    session_id: str


class ChatSource(BaseModel):
    video_id: str
    title: str
    creator: str
    chunk_index: int
