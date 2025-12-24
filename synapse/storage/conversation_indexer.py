"""Conversation indexer for semantic search across chat history.

Indexes conversation messages for semantic retrieval,
enabling search across all past conversations.
"""

from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import json

import tiktoken
from openai import AsyncOpenAI

from . import Chunk, ParentDocument, SessionRecord
from .vector_store_client import FAISSVectorStore
from ..config.settings import get_api_key


# Max tokens for text-embedding-3-small (with safety margin)
MAX_EMBEDDING_TOKENS = 6000

# Token encoder for the embedding model
_encoder: Optional[tiktoken.Encoding] = None


def _get_encoder() -> tiktoken.Encoding:
    """Get or create tiktoken encoder."""
    global _encoder
    if _encoder is None:
        _encoder = tiktoken.get_encoding("cl100k_base")  # GPT-4/embedding model encoding
    return _encoder


def _count_tokens(text: str) -> int:
    """Count tokens in text.

    Args:
        text: Text to count tokens for

    Returns:
        Token count
    """
    encoder = _get_encoder()
    return len(encoder.encode(text))


def _chunk_text(text: str, max_tokens: int = MAX_EMBEDDING_TOKENS) -> List[str]:
    """Split text into chunks under max_tokens.

    Args:
        text: Text to chunk
        max_tokens: Maximum tokens per chunk

    Returns:
        List of text chunks
    """
    encoder = _get_encoder()
    tokens = encoder.encode(text)

    if len(tokens) <= max_tokens:
        return [text]

    chunks = []
    for i in range(0, len(tokens), max_tokens):
        chunk_tokens = tokens[i:i + max_tokens]
        chunks.append(encoder.decode(chunk_tokens))

    return chunks


class ConversationSearchResult:
    """Result from a conversation search."""

    def __init__(
        self,
        message_content: str,
        role: str,
        session_id: str,
        session_date: datetime,
        similarity_score: float,
        context_before: Optional[str] = None,
        context_after: Optional[str] = None,
    ) -> None:
        self.message_content = message_content
        self.role = role
        self.session_id = session_id
        self.session_date = session_date
        self.similarity_score = similarity_score
        self.context_before = context_before
        self.context_after = context_after


class ConversationIndexer:
    """Indexes conversation messages for semantic search.

    Uses a separate vector store from document RAG to keep
    conversation search isolated.
    """

    def __init__(
        self,
        index_path: Optional[Path] = None,
        embedding_model: str = "text-embedding-3-small",
    ) -> None:
        """Initialize the conversation indexer.

        Args:
            index_path: Path to persist the index
            embedding_model: OpenAI embedding model to use
        """
        self._index_path = index_path
        self._embedding_model = embedding_model

        # Initialize vector store
        self._vector_store = FAISSVectorStore(
            dimension=1536,  # text-embedding-3-small
            index_path=index_path,
        )

        # Session metadata storage
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._message_contexts: Dict[str, Dict[str, Any]] = {}

        # Load existing metadata
        if index_path:
            self._load_metadata()

        # OpenAI client (lazy init)
        self._openai: Optional[AsyncOpenAI] = None

    def _get_openai(self) -> AsyncOpenAI:
        """Get or create OpenAI client."""
        if self._openai is None:
            api_key = get_api_key("openai")
            if not api_key:
                raise ValueError(
                    "OPENAI_API_KEY is required for semantic search. "
                    "Please set the environment variable."
                )
            self._openai = AsyncOpenAI(api_key=api_key)
        return self._openai

    async def index_session(self, session: SessionRecord) -> int:
        """Index all messages from a session.

        Args:
            session: The session record to index

        Returns:
            Number of messages indexed
        """
        if not session.messages:
            return 0

        # Store session metadata
        self._sessions[session.session_id] = {
            "started_at": session.started_at.isoformat(),
            "models_used": session.models_used,
        }

        # Create chunks from messages (with token-based chunking for long messages)
        chunks = []
        for i, msg in enumerate(session.messages):
            content = msg.get("content", "")
            if not content or len(content) < 10:  # Skip very short messages
                continue

            # Get context for this message
            context_before = None
            context_after = None
            if i > 0:
                context_before = session.messages[i - 1].get("content", "")[:200]
            if i < len(session.messages) - 1:
                context_after = session.messages[i + 1].get("content", "")[:200]

            # Chunk long messages to stay under embedding model limits
            text_chunks = _chunk_text(content, MAX_EMBEDDING_TOKENS)

            for chunk_idx, text_chunk in enumerate(text_chunks):
                chunk = Chunk.create(
                    content=text_chunk,
                    parent_id=session.session_id,
                    source_file=f"session:{session.session_id}",
                    page_or_section=f"message:{i}" + (f"_part:{chunk_idx}" if len(text_chunks) > 1 else ""),
                    metadata={
                        "role": msg.get("role", "unknown"),
                        "message_index": i,
                        "chunk_index": chunk_idx,
                        "total_chunks": len(text_chunks),
                        "timestamp": msg.get("timestamp", ""),
                    },
                )
                chunks.append(chunk)

                # Store context for later retrieval
                # For chunked messages, use full original content in the result
                self._message_contexts[chunk.chunk_id] = {
                    "context_before": context_before,
                    "context_after": context_after,
                    "role": msg.get("role", "unknown"),
                    "session_id": session.session_id,
                    "session_date": session.started_at.isoformat(),
                    "full_content": content if len(text_chunks) > 1 else None,
                }

        if not chunks:
            return 0

        # Generate embeddings
        chunks = await self._embed_chunks(chunks)

        # Create parent document for the session
        parent = ParentDocument.create(
            source_file=f"session:{session.session_id}",
            title=f"Session {session.session_id[:8]}",
            full_content="",  # Not needed for search
        )
        parent.chunk_ids = [c.chunk_id for c in chunks]

        # Index
        self._vector_store.add_parent(parent)
        self._vector_store.index(chunks, {"session_id": session.session_id})

        # Save metadata
        self._save_metadata()

        return len(chunks)

    async def search(
        self,
        query: str,
        k: int = 10,
    ) -> List[ConversationSearchResult]:
        """Search conversations semantically.

        Args:
            query: Search query
            k: Maximum number of results

        Returns:
            List of search results
        """
        # Get query embedding
        openai = self._get_openai()
        response = await openai.embeddings.create(
            model=self._embedding_model,
            input=[query],
        )
        query_embedding = response.data[0].embedding

        # Search vector store
        results = self._vector_store.query(query_embedding, k=k)

        # Convert to search results
        search_results = []
        for result in results:
            chunk = result.chunk
            ctx = self._message_contexts.get(chunk.chunk_id, {})

            session_date = datetime.now()
            if ctx.get("session_date"):
                try:
                    session_date = datetime.fromisoformat(ctx["session_date"])
                except (ValueError, TypeError):
                    pass

            # Use full_content if this was a chunked message, otherwise use chunk content
            message_content = ctx.get("full_content") or chunk.content

            search_results.append(
                ConversationSearchResult(
                    message_content=message_content,
                    role=ctx.get("role", "unknown"),
                    session_id=ctx.get("session_id", ""),
                    session_date=session_date,
                    similarity_score=result.similarity_score,
                    context_before=ctx.get("context_before"),
                    context_after=ctx.get("context_after"),
                )
            )

        return search_results

    async def _embed_chunks(self, chunks: List[Chunk]) -> List[Chunk]:
        """Generate embeddings for chunks.

        Args:
            chunks: Chunks to embed

        Returns:
            Chunks with embeddings set
        """
        if not chunks:
            return chunks

        openai = self._get_openai()
        texts = [c.content for c in chunks]

        response = await openai.embeddings.create(
            model=self._embedding_model,
            input=texts,
        )

        for i, chunk in enumerate(chunks):
            chunk.embedding = response.data[i].embedding

        return chunks

    def get_indexed_session_count(self) -> int:
        """Get number of indexed sessions."""
        return len(self._sessions)

    def get_indexed_message_count(self) -> int:
        """Get number of indexed messages."""
        return len(self._message_contexts)

    def is_session_indexed(self, session_id: str) -> bool:
        """Check if a session is already indexed."""
        return session_id in self._sessions

    def clear(self) -> None:
        """Clear all indexed data."""
        self._vector_store.clear()
        self._sessions.clear()
        self._message_contexts.clear()
        self._save_metadata()

    def _save_metadata(self) -> None:
        """Save metadata to disk."""
        if not self._index_path:
            return

        self._index_path.mkdir(parents=True, exist_ok=True)

        metadata = {
            "sessions": self._sessions,
            "message_contexts": self._message_contexts,
        }

        with open(self._index_path / "conv_metadata.json", "w") as f:
            json.dump(metadata, f)

    def _load_metadata(self) -> None:
        """Load metadata from disk."""
        if not self._index_path:
            return

        metadata_file = self._index_path / "conv_metadata.json"
        if not metadata_file.exists():
            return

        try:
            with open(metadata_file, "r") as f:
                metadata = json.load(f)
            self._sessions = metadata.get("sessions", {})
            self._message_contexts = metadata.get("message_contexts", {})
        except (json.JSONDecodeError, IOError):
            pass
