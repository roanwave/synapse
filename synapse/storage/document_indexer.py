"""Document indexer for chunking and embedding documents.

Handles PDF, plain text, and other document formats.
Implements parent-document retrieval pattern: index small chunks
for precise recall, return parent blocks for context.
"""

import re
from typing import List, Optional, Callable, Awaitable
from pathlib import Path

from openai import AsyncOpenAI

from . import Chunk, ParentDocument
from .vector_store_client import VectorStoreClient
from .bm25_client import BM25Client
from ..config.settings import get_api_key


# Default chunk sizes (in characters, roughly 4 chars per token)
DEFAULT_CHUNK_SIZE = 2048  # ~512 tokens
DEFAULT_CHUNK_OVERLAP = 200  # ~50 tokens overlap


class DocumentIndexer:
    """Indexes documents for hybrid retrieval.

    Handles document parsing, chunking, embedding, and indexing
    into both vector and BM25 stores.
    """

    def __init__(
        self,
        vector_store: VectorStoreClient,
        bm25_client: BM25Client,
        embedding_model: str = "text-embedding-3-small",
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> None:
        """Initialize the document indexer.

        Args:
            vector_store: Vector store client for semantic search
            bm25_client: BM25 client for keyword search
            embedding_model: OpenAI embedding model to use
            chunk_size: Target chunk size in characters
            chunk_overlap: Overlap between chunks in characters
        """
        self._vector_store = vector_store
        self._bm25_client = bm25_client
        self._embedding_model = embedding_model
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

        # Initialize OpenAI client for embeddings
        api_key = get_api_key("openai")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY is required for embeddings. "
                "Please set the environment variable."
            )
        self._openai = AsyncOpenAI(api_key=api_key)

        # Progress callback
        self._progress_callback: Optional[Callable[[str, float], None]] = None

    def set_progress_callback(
        self, callback: Callable[[str, float], None]
    ) -> None:
        """Set a callback for indexing progress updates.

        Args:
            callback: Function(status_message, progress_0_to_1)
        """
        self._progress_callback = callback

    async def index_document(
        self,
        file_path: Path,
        source_weight: float = 1.0,
    ) -> ParentDocument:
        """Index a document for retrieval.

        Args:
            file_path: Path to the document
            source_weight: Trust weight for this source (0-1)

        Returns:
            The created ParentDocument

        Raises:
            ValueError: If file type is not supported
            FileNotFoundError: If file does not exist
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        self._report_progress("Reading document...", 0.1)

        # Read document content
        content = await self._read_document(file_path)

        # Create parent document
        parent = ParentDocument.create(
            source_file=str(file_path),
            title=file_path.stem,
            full_content=content,
            source_weight=source_weight,
        )

        self._report_progress("Chunking document...", 0.2)

        # Create chunks
        chunks = self._chunk_document(content, parent.doc_id, str(file_path))
        parent.chunk_ids = [c.chunk_id for c in chunks]

        self._report_progress("Generating embeddings...", 0.4)

        # Generate embeddings
        chunks = await self._embed_chunks(chunks)

        self._report_progress("Indexing...", 0.8)

        # Index in vector store
        self._vector_store.add_parent(parent)
        self._vector_store.index(chunks, {"doc_id": parent.doc_id})

        # Index in BM25
        self._bm25_client.index(chunks)

        self._report_progress("Complete", 1.0)

        return parent

    async def index_text(
        self,
        text: str,
        source_name: str,
        source_weight: float = 1.0,
    ) -> ParentDocument:
        """Index raw text for retrieval.

        Args:
            text: The text content
            source_name: Name/identifier for the source
            source_weight: Trust weight for this source (0-1)

        Returns:
            The created ParentDocument
        """
        # Create parent document
        parent = ParentDocument.create(
            source_file=source_name,
            title=source_name,
            full_content=text,
            source_weight=source_weight,
        )

        # Create chunks
        chunks = self._chunk_document(text, parent.doc_id, source_name)
        parent.chunk_ids = [c.chunk_id for c in chunks]

        # Generate embeddings
        chunks = await self._embed_chunks(chunks)

        # Index in vector store
        self._vector_store.add_parent(parent)
        self._vector_store.index(chunks, {"doc_id": parent.doc_id})

        # Index in BM25
        self._bm25_client.index(chunks)

        return parent

    def delete_document(self, doc_id: str) -> None:
        """Delete a document from all indexes.

        Args:
            doc_id: The document ID to delete
        """
        self._vector_store.delete(doc_id)
        self._bm25_client.delete(doc_id)

    async def _read_document(self, file_path: Path) -> str:
        """Read document content based on file type.

        Args:
            file_path: Path to the document

        Returns:
            Document text content

        Raises:
            ValueError: If file type is not supported
        """
        suffix = file_path.suffix.lower()

        if suffix == ".pdf":
            return await self._read_pdf(file_path)
        elif suffix == ".txt":
            return file_path.read_text(encoding="utf-8")
        elif suffix == ".md":
            return file_path.read_text(encoding="utf-8")
        elif suffix == ".docx":
            return await self._read_docx(file_path)
        else:
            # Try reading as plain text
            try:
                return file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                raise ValueError(f"Unsupported file type: {suffix}")

    async def _read_pdf(self, file_path: Path) -> str:
        """Read PDF file content.

        Args:
            file_path: Path to the PDF

        Returns:
            Extracted text content
        """
        try:
            import pypdf
        except ImportError:
            raise ImportError(
                "pypdf is required for PDF support. "
                "Install with: pip install pypdf"
            )

        text_parts = []
        with open(file_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    text_parts.append(f"[Page {page_num + 1}]\n{text}")

        return "\n\n".join(text_parts)

    async def _read_docx(self, file_path: Path) -> str:
        """Read DOCX file content.

        Args:
            file_path: Path to the DOCX

        Returns:
            Extracted text content
        """
        try:
            from docx import Document
        except ImportError:
            raise ImportError(
                "python-docx is required for DOCX support. "
                "Install with: pip install python-docx"
            )

        doc = Document(str(file_path))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)

    def _chunk_document(
        self,
        content: str,
        parent_id: str,
        source_file: str,
    ) -> List[Chunk]:
        """Split document into chunks.

        Uses sentence-aware splitting to avoid breaking mid-sentence.

        Args:
            content: Document content
            parent_id: Parent document ID
            source_file: Source file path

        Returns:
            List of Chunk objects
        """
        chunks = []

        # Split into paragraphs first
        paragraphs = re.split(r'\n\s*\n', content)

        current_chunk = ""
        current_section = ""
        chunk_index = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Check for section headers (simple heuristic)
            if self._is_section_header(para):
                current_section = para[:50]  # Truncate long headers

            # If adding this paragraph exceeds chunk size, save current chunk
            if (
                current_chunk
                and len(current_chunk) + len(para) > self._chunk_size
            ):
                chunks.append(
                    Chunk.create(
                        content=current_chunk.strip(),
                        parent_id=parent_id,
                        source_file=source_file,
                        page_or_section=current_section or f"Chunk {chunk_index + 1}",
                    )
                )
                chunk_index += 1

                # Keep overlap from end of current chunk
                if self._chunk_overlap > 0:
                    overlap_text = current_chunk[-self._chunk_overlap:]
                    current_chunk = overlap_text + "\n\n" + para
                else:
                    current_chunk = para
            else:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para

        # Add final chunk
        if current_chunk.strip():
            chunks.append(
                Chunk.create(
                    content=current_chunk.strip(),
                    parent_id=parent_id,
                    source_file=source_file,
                    page_or_section=current_section or f"Chunk {chunk_index + 1}",
                )
            )

        return chunks

    def _is_section_header(self, text: str) -> bool:
        """Check if text looks like a section header.

        Args:
            text: Text to check

        Returns:
            True if likely a header
        """
        # Short text that doesn't end with punctuation
        if len(text) < 100 and not text.endswith(('.', '?', '!', ',')):
            return True
        # Markdown headers
        if text.startswith('#'):
            return True
        # Numbered sections
        if re.match(r'^[\d.]+\s+[A-Z]', text):
            return True
        return False

    async def _embed_chunks(self, chunks: List[Chunk]) -> List[Chunk]:
        """Generate embeddings for chunks.

        Args:
            chunks: Chunks to embed

        Returns:
            Chunks with embeddings set
        """
        if not chunks:
            return chunks

        # Batch embed for efficiency
        texts = [c.content for c in chunks]

        response = await self._openai.embeddings.create(
            model=self._embedding_model,
            input=texts,
        )

        for i, chunk in enumerate(chunks):
            chunk.embedding = response.data[i].embedding

        return chunks

    async def get_query_embedding(self, query: str) -> List[float]:
        """Get embedding for a query string.

        Args:
            query: The query text

        Returns:
            Embedding vector
        """
        response = await self._openai.embeddings.create(
            model=self._embedding_model,
            input=[query],
        )
        return response.data[0].embedding

    def _report_progress(self, status: str, progress: float) -> None:
        """Report indexing progress.

        Args:
            status: Status message
            progress: Progress from 0 to 1
        """
        if self._progress_callback:
            self._progress_callback(status, progress)
