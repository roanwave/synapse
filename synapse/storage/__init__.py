"""Storage module for persistence and retrieval.

This module handles all data storage including:
- Vector store for semantic search (FAISS)
- BM25 for keyword search
- Document indexing and chunking
- Conversation archives
- Retrieval blacklists
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
import uuid


@dataclass
class Chunk:
    """A chunk of text for indexing and retrieval."""

    chunk_id: str
    parent_id: str
    content: str
    source_file: str
    page_or_section: str = ""
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        content: str,
        parent_id: str,
        source_file: str,
        page_or_section: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "Chunk":
        """Create a new chunk with generated ID.

        Args:
            content: The text content
            parent_id: ID of the parent document
            source_file: Source file path
            page_or_section: Page number or section identifier
            metadata: Additional metadata

        Returns:
            New Chunk instance
        """
        return cls(
            chunk_id=str(uuid.uuid4()),
            parent_id=parent_id,
            content=content,
            source_file=source_file,
            page_or_section=page_or_section,
            metadata=metadata or {},
        )


@dataclass
class ParentDocument:
    """A parent document containing multiple chunks."""

    doc_id: str
    source_file: str
    title: str
    full_content: str
    chunk_ids: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    source_weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        source_file: str,
        title: str,
        full_content: str,
        source_weight: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "ParentDocument":
        """Create a new parent document with generated ID.

        Args:
            source_file: Source file path
            title: Document title
            full_content: Full document content
            source_weight: User-configurable trust level
            metadata: Additional metadata

        Returns:
            New ParentDocument instance
        """
        return cls(
            doc_id=str(uuid.uuid4()),
            source_file=source_file,
            title=title,
            full_content=full_content,
            source_weight=source_weight,
            metadata=metadata or {},
        )


@dataclass
class RetrievalResult:
    """Result from a retrieval query."""

    chunk: Chunk
    similarity_score: float
    recency_weight: float = 1.0
    source_weight: float = 1.0
    parent_document: Optional[ParentDocument] = None

    @property
    def combined_score(self) -> float:
        """Calculate combined relevance score.

        Returns:
            Weighted combination of similarity, recency, and source trust
        """
        return (
            self.similarity_score * 0.6
            + self.recency_weight * 0.2
            + self.source_weight * 0.2
        )


@dataclass
class ChunkMetadata:
    """Metadata for RAG injection into prompts."""

    chunk_id: str
    parent_id: str
    source_file: str
    page_or_section: str
    similarity_score: float
    recency_weight: float
    source_weight: float
    blacklisted_topics: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "chunk_id": self.chunk_id,
            "parent_id": self.parent_id,
            "source_file": self.source_file,
            "page_or_section": self.page_or_section,
            "similarity_score": self.similarity_score,
            "recency_weight": self.recency_weight,
            "source_weight": self.source_weight,
            "blacklisted_topics": self.blacklisted_topics,
        }


@dataclass
class SessionRecord:
    """Record of a conversation session for archival."""

    session_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    models_used: List[str] = field(default_factory=list)
    summary_xml: str = ""
    token_count: int = 0
    drift_events: int = 0
    waypoints: List[Dict[str, Any]] = field(default_factory=list)
    artifacts_generated: List[str] = field(default_factory=list)
    messages: List[Dict[str, str]] = field(default_factory=list)
    # Fork tracking
    fork_source_session_id: Optional[str] = None
    fork_point_index: Optional[int] = None

    @classmethod
    def create(cls) -> "SessionRecord":
        """Create a new session record.

        Returns:
            New SessionRecord instance
        """
        return cls(
            session_id=str(uuid.uuid4()),
            started_at=datetime.now(),
        )

    @classmethod
    def create_fork(
        cls,
        source_session_id: str,
        fork_point_index: int,
        messages: List[Dict[str, str]],
        models_used: Optional[List[str]] = None,
    ) -> "SessionRecord":
        """Create a new session record as a fork of another session.

        Args:
            source_session_id: ID of the session being forked
            fork_point_index: Message index where fork occurs
            messages: Messages up to the fork point
            models_used: Models used in the source session

        Returns:
            New SessionRecord instance for the fork
        """
        return cls(
            session_id=str(uuid.uuid4()),
            started_at=datetime.now(),
            models_used=models_used or [],
            messages=messages,
            fork_source_session_id=source_session_id,
            fork_point_index=fork_point_index,
        )

    @property
    def is_fork(self) -> bool:
        """Check if this session is a fork of another."""
        return self.fork_source_session_id is not None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = {
            "session_id": self.session_id,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "models_used": self.models_used,
            "summary_xml": self.summary_xml,
            "token_count": self.token_count,
            "drift_events": self.drift_events,
            "waypoints": self.waypoints,
            "artifacts_generated": self.artifacts_generated,
            "messages": self.messages,
        }
        if self.fork_source_session_id:
            data["fork_source_session_id"] = self.fork_source_session_id
            data["fork_point_index"] = self.fork_point_index
        return data


__all__ = [
    "Chunk",
    "ParentDocument",
    "RetrievalResult",
    "ChunkMetadata",
    "SessionRecord",
]
