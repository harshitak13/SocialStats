import asyncio
from typing import Any

from dotenv import load_dotenv
from langchain_classic.memory import ConversationBufferMemory
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from db.chroma_client import chroma_client


load_dotenv()


session_memories: dict[str, ConversationBufferMemory] = {}

SYSTEM_PROMPT = """
You are SocialStats AI, an expert social media analyst.
You help creators understand why their videos perform the way they do.

When answering:
- Always cite which video (Video A or Video B) your answer comes from
- Always mention the chunk index when referencing specific content
- Be specific with numbers - engagement rates, views, likes, comments
- If comparing videos, structure your answer clearly with A vs B sections
- If asked about hooks, reference the first transcript chunks (chunk_0)

Context from video transcripts:
{context}

Chat history:
{chat_history}

Question: {question}

Answer with citations in this format at the end of your response:
Sources: [Video X, Chunk Y] [Video X, Chunk Z]
"""


def get_or_create_memory(session_id: str) -> ConversationBufferMemory:
    """Return the conversation memory for a session, creating it when needed."""
    if session_id not in session_memories:
        session_memories[session_id] = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="answer",
        )
    return session_memories[session_id]


def _build_retriever() -> Any:
    """Build the SocialStats Chroma retriever for transcript chunks."""
    return Chroma(
        client=chroma_client,
        collection_name="socialstats_transcripts",
        embedding_function=OpenAIEmbeddings(model="text-embedding-3-small"),
    ).as_retriever(search_kwargs={"k": 5})


def _build_llm() -> ChatOpenAI:
    """Build the streaming GPT-4o chat model used by SocialStats."""
    return ChatOpenAI(model="gpt-4o", streaming=True, temperature=0.3)


def _format_chat_history(chat_history: list[Any]) -> str:
    """Render stored chat messages as prompt-ready plain text."""
    if not chat_history:
        return "No previous messages."

    lines = []
    for message in chat_history:
        role = getattr(message, "type", "message")
        content = getattr(message, "content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _format_docs(docs: list[Document]) -> str:
    """Format retrieved transcript chunks with video and chunk citations."""
    if not docs:
        return "No transcript chunks were retrieved."

    chunks = []
    for doc in docs:
        metadata = doc.metadata or {}
        video_id = metadata.get("video_id", "unknown")
        chunk_index = metadata.get("chunk_index", "unknown")
        title = metadata.get("title", "Untitled")
        creator = metadata.get("creator", "Unknown creator")
        engagement_rate = metadata.get("engagement_rate", "unknown")
        chunks.append(
            "\n".join(
                [
                    f"Video {video_id}, Chunk {chunk_index}",
                    f"Title: {title}",
                    f"Creator: {creator}",
                    f"Engagement rate: {engagement_rate}",
                    f"Transcript: {doc.page_content}",
                ]
            )
        )
    return "\n\n".join(chunks)


def _source_footer(docs: list[Document]) -> str:
    """Create the required source citation footer for retrieved documents."""
    if not docs:
        return "Sources: []"

    citations = []
    for doc in docs:
        metadata = doc.metadata or {}
        video_id = metadata.get("video_id", "unknown")
        chunk_index = metadata.get("chunk_index", "unknown")
        citations.append(f"[Video {video_id}, Chunk {chunk_index}]")
    return "Sources: " + " ".join(citations)


class SocialStatsRAGChain:
    """Small async streaming wrapper around SocialStats retrieval, memory, and LLM."""

    def __init__(
        self,
        retriever: Any,
        llm: ChatOpenAI,
        memory: ConversationBufferMemory,
    ) -> None:
        """Create a session-scoped RAG chain wrapper."""
        self.retriever = retriever
        self.llm = llm
        self.memory = memory
        self.prompt = ChatPromptTemplate.from_template(SYSTEM_PROMPT)

    async def astream(self, inputs: dict[str, str]) -> Any:
        """Stream an answer token by token for a SocialStats chat question."""
        question = inputs["question"]
        docs = await asyncio.to_thread(self.retriever.invoke, question)
        memory_values = self.memory.load_memory_variables({})
        chat_history = _format_chat_history(memory_values.get("chat_history", []))
        context = _format_docs(docs)
        messages = self.prompt.format_messages(
            context=context,
            chat_history=chat_history,
            question=question,
        )

        answer_parts = []
        async for chunk in self.llm.astream(messages):
            token = str(getattr(chunk, "content", "") or "")
            if token:
                answer_parts.append(token)
                yield token

        footer = "\n\n" + _source_footer(docs)
        answer_parts.append(footer)
        yield footer

        self.memory.save_context(
            {"question": question},
            {"answer": "".join(answer_parts)},
        )


def get_rag_chain(session_id: str) -> SocialStatsRAGChain:
    """Return a session-configured SocialStats RAG chain with memory."""
    memory = get_or_create_memory(session_id)
    retriever = _build_retriever()
    llm = _build_llm()
    return SocialStatsRAGChain(retriever=retriever, llm=llm, memory=memory)
