# SocialStats

AI-powered social media video analytics with RAG chat.

## What it does

- Takes a YouTube URL and Instagram Reel URL
- Pulls transcripts and metadata dynamically
- Computes engagement rates
- Embeds transcripts into ChromaDB vector store
- Streams RAG-powered chat with source citations and memory

## Tech Stack

- Frontend: React + Vite + Tailwind CSS
- Backend: FastAPI + Python
- Orchestration: LangChain (ConversationalRetrievalChain)
- Embeddings: OpenAI text-embedding-3-small
- Vector DB: ChromaDB (persistent local store)
- LLM: GPT-4o with streaming
- Transcripts: youtube-transcript-api + yt-dlp + OpenAI Whisper

## Why this stack?

- text-embedding-3-small: $0.00002/1K tokens, the cheapest quality embedding
- ChromaDB: zero infra cost, runs locally, migrates to Qdrant at scale
- GPT-4o: faster and cheaper than GPT-4-turbo at similar quality
- At 1000 creators/day: around $0.06/day embeddings plus around $10/day chat, under $400/month total

## Setup

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
```

Add your `OPENAI_API_KEY` to `.env`.

```bash
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Usage

1. Open http://localhost:3000
2. Paste a YouTube URL and Instagram Reel URL
3. Click "Analyze with SocialStats"
4. Wait for ingestion, usually around 30 seconds depending on transcript and Whisper work
5. Chat with your video data

## Scalability Notes

- At 10K users: replace ChromaDB with Qdrant Cloud
- Add Redis for session memory instead of an in-memory dict
- Add Celery + Redis queue for ingest jobs
- Instagram follower count requires Apify or RapidAPI paid tier
