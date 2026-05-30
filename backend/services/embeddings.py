import asyncio

from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings

from db.chroma_client import collection
from models.schemas import VideoMetadata


load_dotenv()


def _delete_existing_chunks(video_id: str) -> None:
    """Delete existing SocialStats transcript chunks for a video."""
    collection.delete(where={"video_id": video_id})


def _store_chunks(metadata: VideoMetadata) -> int:
    """Split, embed, and store transcript chunks for one video."""
    _delete_existing_chunks(metadata.video_id)

    if not metadata.transcript.strip():
        # NOTE: Some videos do not expose transcript data, so there is nothing to embed.
        return 0

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_text(metadata.transcript)
    if not chunks:
        return 0

    embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")
    vectors = embeddings_model.embed_documents(chunks)
    ids = [f"{metadata.video_id}_chunk_{index}" for index in range(len(chunks))]
    metadatas = [
        {
            "video_id": metadata.video_id,
            "title": metadata.title,
            "creator": metadata.creator,
            "engagement_rate": metadata.engagement_rate,
            "chunk_index": index,
        }
        for index in range(len(chunks))
    ]

    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=vectors,
        metadatas=metadatas,
    )
    return len(chunks)


async def embed_and_store(metadata: VideoMetadata) -> int:
    """Embed a video's transcript chunks and return the number stored."""
    return await asyncio.to_thread(_store_chunks, metadata)
