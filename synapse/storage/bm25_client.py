"""BM25 keyword search client for hybrid retrieval.

Pure vector search fails on error codes, acronyms, code identifiers,
and technical terms. BM25 provides keyword-based matching to complement
semantic search.
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from . import Chunk, RetrievalResult


@dataclass
class BM25Result:
    """Result from BM25 search."""

    chunk_id: str
    score: float


class BM25Client:
    """BM25 keyword search implementation.

    Uses rank-bm25 library for efficient keyword matching.
    Designed to work alongside vector search for hybrid retrieval.
    """

    def __init__(self) -> None:
        """Initialize the BM25 client."""
        try:
            from rank_bm25 import BM25Okapi
            self._bm25_class = BM25Okapi
        except ImportError:
            raise ImportError(
                "rank-bm25 is required for keyword search. "
                "Install with: pip install rank-bm25"
            )

        self._bm25: Optional[object] = None
        self._chunks: Dict[str, Chunk] = {}  # chunk_id -> Chunk
        self._chunk_ids: List[str] = []  # Ordered list matching BM25 corpus
        self._tokenized_corpus: List[List[str]] = []

    def index(self, chunks: List[Chunk]) -> None:
        """Index chunks for BM25 search.

        Args:
            chunks: List of chunks to index
        """
        if not chunks:
            return

        # Add new chunks
        for chunk in chunks:
            if chunk.chunk_id not in self._chunks:
                self._chunks[chunk.chunk_id] = chunk
                self._chunk_ids.append(chunk.chunk_id)
                tokens = self._tokenize(chunk.content)
                self._tokenized_corpus.append(tokens)

        # Rebuild BM25 index
        if self._tokenized_corpus:
            self._bm25 = self._bm25_class(self._tokenized_corpus)

    def query(self, query: str, k: int = 5) -> List[BM25Result]:
        """Query for matching chunks.

        Args:
            query: The search query
            k: Number of results to return

        Returns:
            List of BM25Result ordered by score
        """
        if not self._bm25 or not self._chunk_ids:
            return []

        # Tokenize query
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        # Get BM25 scores
        scores = self._bm25.get_scores(query_tokens)

        # Get top k results
        scored_indices = [(i, score) for i, score in enumerate(scores)]
        scored_indices.sort(key=lambda x: x[1], reverse=True)

        results = []
        for idx, score in scored_indices[:k]:
            if score > 0:  # Only include positive scores
                chunk_id = self._chunk_ids[idx]
                results.append(BM25Result(chunk_id=chunk_id, score=float(score)))

        return results

    def delete(self, doc_id: str) -> None:
        """Delete all chunks for a document.

        Args:
            doc_id: The parent document ID to delete
        """
        # Find and remove chunks belonging to this document
        chunks_to_remove = [
            cid for cid, chunk in self._chunks.items()
            if chunk.parent_id == doc_id
        ]

        for chunk_id in chunks_to_remove:
            if chunk_id in self._chunks:
                del self._chunks[chunk_id]

        # Rebuild corpus and index
        self._rebuild()

    def clear(self) -> None:
        """Clear all indexed data."""
        self._bm25 = None
        self._chunks.clear()
        self._chunk_ids.clear()
        self._tokenized_corpus.clear()

    def get_chunk(self, chunk_id: str) -> Optional[Chunk]:
        """Get a chunk by ID.

        Args:
            chunk_id: The chunk ID

        Returns:
            Chunk if found, None otherwise
        """
        return self._chunks.get(chunk_id)

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text for BM25.

        Handles code identifiers, camelCase, and technical terms.

        Args:
            text: Text to tokenize

        Returns:
            List of tokens
        """
        # Convert to lowercase
        text = text.lower()

        # Split camelCase and snake_case
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        text = re.sub(r'_', ' ', text)

        # Keep alphanumeric, dots (for file extensions), and hyphens
        text = re.sub(r'[^a-z0-9.\-\s]', ' ', text)

        # Split and filter
        tokens = text.split()
        tokens = [t.strip() for t in tokens if len(t.strip()) > 1]

        return tokens

    def _rebuild(self) -> None:
        """Rebuild the BM25 index from stored chunks."""
        self._chunk_ids = list(self._chunks.keys())
        self._tokenized_corpus = [
            self._tokenize(self._chunks[cid].content)
            for cid in self._chunk_ids
        ]

        if self._tokenized_corpus:
            self._bm25 = self._bm25_class(self._tokenized_corpus)
        else:
            self._bm25 = None


def reciprocal_rank_fusion(
    vector_results: List[RetrievalResult],
    bm25_results: List[BM25Result],
    chunks: Dict[str, Chunk],
    k: int = 60,
) -> List[Tuple[str, float]]:
    """Combine vector and BM25 results using Reciprocal Rank Fusion.

    RRF score = sum(1 / (k + rank)) for each result list.

    Args:
        vector_results: Results from vector search
        bm25_results: Results from BM25 search
        chunks: Dict of chunk_id -> Chunk for lookup
        k: RRF constant (default 60)

    Returns:
        List of (chunk_id, fused_score) tuples, sorted by score
    """
    scores: Dict[str, float] = {}

    # Add vector search scores
    for rank, result in enumerate(vector_results):
        chunk_id = result.chunk.chunk_id
        scores[chunk_id] = scores.get(chunk_id, 0) + 1.0 / (k + rank + 1)

    # Add BM25 scores
    for rank, result in enumerate(bm25_results):
        scores[result.chunk_id] = scores.get(result.chunk_id, 0) + 1.0 / (k + rank + 1)

    # Sort by fused score
    sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    return sorted_results
