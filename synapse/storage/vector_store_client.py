"""Vector store client for semantic search.

FAISS is the default implementation. Swapping to another store
should be a one-file change - never let FAISS-specific assumptions
leak into orchestrator or LLM layers.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from pathlib import Path
import json
import pickle

import numpy as np

from . import Chunk, ParentDocument, RetrievalResult


class VectorStoreClient(ABC):
    """Abstract interface for vector store operations.

    All retrieval goes through this interface. Implementations must be
    stateless with respect to conversations - they only manage document
    embeddings and retrieval.
    """

    @abstractmethod
    def index(self, chunks: List[Chunk], metadata: Dict[str, Any]) -> None:
        """Index chunks with their embeddings.

        Args:
            chunks: List of chunks to index (must have embeddings set)
            metadata: Additional metadata for the indexing operation
        """
        ...

    @abstractmethod
    def query(
        self,
        query_embedding: List[float],
        k: int = 5,
        filter_doc_ids: Optional[List[str]] = None,
    ) -> List[RetrievalResult]:
        """Query for similar chunks.

        Args:
            query_embedding: The query vector
            k: Number of results to return
            filter_doc_ids: Optional list of doc IDs to filter to

        Returns:
            List of RetrievalResult ordered by similarity
        """
        ...

    @abstractmethod
    def delete(self, doc_id: str) -> None:
        """Delete all chunks for a document.

        Args:
            doc_id: The parent document ID to delete
        """
        ...

    @abstractmethod
    def get_parent(self, chunk_id: str) -> Optional[ParentDocument]:
        """Get the parent document for a chunk.

        Args:
            chunk_id: The chunk ID

        Returns:
            ParentDocument if found, None otherwise
        """
        ...

    @abstractmethod
    def add_parent(self, parent: ParentDocument) -> None:
        """Add a parent document to the store.

        Args:
            parent: The parent document to store
        """
        ...

    @abstractmethod
    def get_all_doc_ids(self) -> List[str]:
        """Get all indexed document IDs.

        Returns:
            List of document IDs
        """
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear all indexed data."""
        ...


class FAISSVectorStore(VectorStoreClient):
    """FAISS-based vector store implementation.

    Uses FAISS for efficient similarity search with cosine similarity.
    Stores metadata separately for chunk/parent lookup.
    """

    def __init__(
        self,
        dimension: int = 1536,  # text-embedding-3-small dimension
        index_path: Optional[Path] = None,
    ) -> None:
        """Initialize the FAISS vector store.

        Args:
            dimension: Embedding dimension (default 1536 for OpenAI)
            index_path: Optional path to persist the index
        """
        # Lazy import to avoid startup cost if not used
        try:
            import faiss
        except ImportError:
            raise ImportError(
                "faiss-cpu is required for vector search. "
                "Install with: pip install faiss-cpu"
            )

        self._dimension = dimension
        self._index_path = index_path
        self._faiss = faiss

        # Initialize FAISS index with cosine similarity (normalized L2)
        self._index = faiss.IndexFlatIP(dimension)  # Inner product for cosine sim

        # Metadata storage
        self._chunks: Dict[str, Chunk] = {}  # chunk_id -> Chunk
        self._parents: Dict[str, ParentDocument] = {}  # doc_id -> ParentDocument
        self._id_to_idx: Dict[str, int] = {}  # chunk_id -> FAISS index
        self._idx_to_id: Dict[int, str] = {}  # FAISS index -> chunk_id
        self._next_idx = 0

        # Load existing index if path provided
        if index_path and index_path.exists():
            self._load()

    def index(self, chunks: List[Chunk], metadata: Dict[str, Any]) -> None:
        """Index chunks with their embeddings.

        Args:
            chunks: List of chunks to index (must have embeddings set)
            metadata: Additional metadata (unused currently)
        """
        if not chunks:
            return

        # Prepare embeddings matrix
        embeddings = []
        for chunk in chunks:
            if chunk.embedding is None:
                raise ValueError(f"Chunk {chunk.chunk_id} has no embedding")
            embeddings.append(chunk.embedding)

        # Normalize embeddings for cosine similarity
        embeddings_np = np.array(embeddings, dtype=np.float32)
        self._faiss.normalize_L2(embeddings_np)

        # Add to FAISS index
        self._index.add(embeddings_np)

        # Store metadata
        for i, chunk in enumerate(chunks):
            idx = self._next_idx + i
            self._chunks[chunk.chunk_id] = chunk
            self._id_to_idx[chunk.chunk_id] = idx
            self._idx_to_id[idx] = chunk.chunk_id

        self._next_idx += len(chunks)

        # Persist if path configured
        if self._index_path:
            self._save()

    def query(
        self,
        query_embedding: List[float],
        k: int = 5,
        filter_doc_ids: Optional[List[str]] = None,
    ) -> List[RetrievalResult]:
        """Query for similar chunks.

        Args:
            query_embedding: The query vector
            k: Number of results to return
            filter_doc_ids: Optional list of doc IDs to filter to

        Returns:
            List of RetrievalResult ordered by similarity
        """
        if self._index.ntotal == 0:
            return []

        # Normalize query for cosine similarity
        query_np = np.array([query_embedding], dtype=np.float32)
        self._faiss.normalize_L2(query_np)

        # Search with larger k if filtering
        search_k = k * 3 if filter_doc_ids else k
        search_k = min(search_k, self._index.ntotal)

        distances, indices = self._index.search(query_np, search_k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0:  # FAISS returns -1 for unfilled slots
                continue

            chunk_id = self._idx_to_id.get(idx)
            if not chunk_id:
                continue

            chunk = self._chunks.get(chunk_id)
            if not chunk:
                continue

            # Apply document filter if specified
            if filter_doc_ids and chunk.parent_id not in filter_doc_ids:
                continue

            # Get parent document
            parent = self._parents.get(chunk.parent_id)

            # Create result with similarity score (dist is cosine sim for IP)
            result = RetrievalResult(
                chunk=chunk,
                similarity_score=float(dist),
                source_weight=parent.source_weight if parent else 1.0,
                parent_document=parent,
            )
            results.append(result)

            if len(results) >= k:
                break

        return results

    def delete(self, doc_id: str) -> None:
        """Delete all chunks for a document.

        Note: FAISS IndexFlatIP doesn't support deletion, so we mark
        chunks as deleted and rebuild periodically.

        Args:
            doc_id: The parent document ID to delete
        """
        # Remove from parents
        if doc_id in self._parents:
            parent = self._parents.pop(doc_id)
            # Remove all associated chunks
            for chunk_id in parent.chunk_ids:
                if chunk_id in self._chunks:
                    del self._chunks[chunk_id]
                if chunk_id in self._id_to_idx:
                    idx = self._id_to_idx.pop(chunk_id)
                    if idx in self._idx_to_id:
                        del self._idx_to_id[idx]

        # Rebuild index without deleted chunks
        self._rebuild_index()

        if self._index_path:
            self._save()

    def get_parent(self, chunk_id: str) -> Optional[ParentDocument]:
        """Get the parent document for a chunk.

        Args:
            chunk_id: The chunk ID

        Returns:
            ParentDocument if found, None otherwise
        """
        chunk = self._chunks.get(chunk_id)
        if chunk:
            return self._parents.get(chunk.parent_id)
        return None

    def add_parent(self, parent: ParentDocument) -> None:
        """Add a parent document to the store.

        Args:
            parent: The parent document to store
        """
        self._parents[parent.doc_id] = parent

        if self._index_path:
            self._save()

    def get_all_doc_ids(self) -> List[str]:
        """Get all indexed document IDs.

        Returns:
            List of document IDs
        """
        return list(self._parents.keys())

    def clear(self) -> None:
        """Clear all indexed data."""
        self._index = self._faiss.IndexFlatIP(self._dimension)
        self._chunks.clear()
        self._parents.clear()
        self._id_to_idx.clear()
        self._idx_to_id.clear()
        self._next_idx = 0

        if self._index_path:
            self._save()

    def _rebuild_index(self) -> None:
        """Rebuild the FAISS index from stored chunks."""
        # Create new index
        self._index = self._faiss.IndexFlatIP(self._dimension)
        self._id_to_idx.clear()
        self._idx_to_id.clear()
        self._next_idx = 0

        # Re-index all remaining chunks
        chunks_with_embeddings = [
            c for c in self._chunks.values() if c.embedding is not None
        ]
        if chunks_with_embeddings:
            embeddings = [c.embedding for c in chunks_with_embeddings]
            embeddings_np = np.array(embeddings, dtype=np.float32)
            self._faiss.normalize_L2(embeddings_np)
            self._index.add(embeddings_np)

            for i, chunk in enumerate(chunks_with_embeddings):
                self._id_to_idx[chunk.chunk_id] = i
                self._idx_to_id[i] = chunk.chunk_id
                self._next_idx = i + 1

    def _save(self) -> None:
        """Save index and metadata to disk."""
        if not self._index_path:
            return

        self._index_path.mkdir(parents=True, exist_ok=True)

        # Save FAISS index
        self._faiss.write_index(
            self._index, str(self._index_path / "faiss.index")
        )

        # Save metadata
        metadata = {
            "dimension": self._dimension,
            "next_idx": self._next_idx,
            "id_to_idx": self._id_to_idx,
            "idx_to_id": {str(k): v for k, v in self._idx_to_id.items()},
        }
        with open(self._index_path / "metadata.json", "w") as f:
            json.dump(metadata, f)

        # Save chunks and parents (pickle for dataclasses)
        with open(self._index_path / "chunks.pkl", "wb") as f:
            pickle.dump(self._chunks, f)

        with open(self._index_path / "parents.pkl", "wb") as f:
            pickle.dump(self._parents, f)

    def _load(self) -> None:
        """Load index and metadata from disk."""
        if not self._index_path or not self._index_path.exists():
            return

        try:
            # Load FAISS index
            index_file = self._index_path / "faiss.index"
            if index_file.exists():
                self._index = self._faiss.read_index(str(index_file))

            # Load metadata
            metadata_file = self._index_path / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)
                self._dimension = metadata.get("dimension", self._dimension)
                self._next_idx = metadata.get("next_idx", 0)
                self._id_to_idx = metadata.get("id_to_idx", {})
                self._idx_to_id = {
                    int(k): v for k, v in metadata.get("idx_to_id", {}).items()
                }

            # Load chunks and parents
            chunks_file = self._index_path / "chunks.pkl"
            if chunks_file.exists():
                with open(chunks_file, "rb") as f:
                    self._chunks = pickle.load(f)

            parents_file = self._index_path / "parents.pkl"
            if parents_file.exists():
                with open(parents_file, "rb") as f:
                    self._parents = pickle.load(f)

        except Exception:
            # If loading fails, start fresh
            self.clear()
