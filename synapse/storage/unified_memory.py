"""Unified memory for persistent facts across conversations.

Stores user preferences, facts, and context that persist
between conversation sessions.
"""

import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import uuid


@dataclass
class MemoryFact:
    """A single fact stored in unified memory."""

    fact_id: str
    content: str
    category: str  # "preference", "fact", "person", "project", "custom"
    created_at: datetime
    source_session: Optional[str] = None
    keywords: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "fact_id": self.fact_id,
            "content": self.content,
            "category": self.category,
            "created_at": self.created_at.isoformat(),
            "source_session": self.source_session,
            "keywords": self.keywords,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryFact":
        """Create from dictionary.

        Args:
            data: Dictionary from JSON

        Returns:
            MemoryFact instance
        """
        return cls(
            fact_id=data["fact_id"],
            content=data["content"],
            category=data.get("category", "fact"),
            created_at=datetime.fromisoformat(data["created_at"]),
            source_session=data.get("source_session"),
            keywords=data.get("keywords", []),
        )

    @classmethod
    def create(
        cls,
        content: str,
        category: str = "fact",
        source_session: Optional[str] = None,
    ) -> "MemoryFact":
        """Create a new memory fact.

        Args:
            content: The fact content
            category: Category of the fact
            source_session: Session ID where fact was created

        Returns:
            New MemoryFact instance
        """
        # Extract simple keywords
        keywords = cls._extract_keywords(content)

        return cls(
            fact_id=str(uuid.uuid4()),
            content=content,
            category=category,
            created_at=datetime.now(),
            source_session=source_session,
            keywords=keywords,
        )

    @staticmethod
    def _extract_keywords(content: str) -> List[str]:
        """Extract simple keywords from content.

        Args:
            content: Text to extract keywords from

        Returns:
            List of lowercase keywords
        """
        # Simple keyword extraction - words > 4 chars, not common words
        stop_words = {
            "the", "and", "that", "this", "with", "have", "from",
            "they", "will", "would", "could", "should", "about",
            "their", "there", "which", "when", "what", "where",
            "also", "been", "were", "being", "some", "more", "very",
        }

        words = content.lower().split()
        keywords = []
        for word in words:
            # Clean punctuation
            clean = "".join(c for c in word if c.isalnum())
            if len(clean) > 4 and clean not in stop_words:
                keywords.append(clean)

        return list(set(keywords))[:10]  # Max 10 keywords


class UnifiedMemory:
    """Manages persistent memory across conversations.

    Memory categories:
    - preference: User preferences (coding style, communication preferences)
    - fact: General facts the user wants remembered
    - person: Information about people
    - project: Project-specific context
    - custom: User-defined category
    """

    CATEGORIES = ["preference", "fact", "person", "project", "custom"]

    def __init__(self, storage_path: Path) -> None:
        """Initialize unified memory.

        Args:
            storage_path: Path to the memory JSON file
        """
        self._storage_path = storage_path
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._facts: List[MemoryFact] = []
        self._load()

    def _load(self) -> None:
        """Load facts from storage file."""
        if not self._storage_path.exists():
            return

        try:
            with open(self._storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._facts = [
                    MemoryFact.from_dict(fact_data)
                    for fact_data in data.get("facts", [])
                ]
        except (json.JSONDecodeError, KeyError):
            # Corrupted file, start fresh
            self._facts = []

    def _save(self) -> None:
        """Save facts to storage file."""
        data = {
            "version": 1,
            "facts": [fact.to_dict() for fact in self._facts],
        }
        with open(self._storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def add_fact(
        self,
        content: str,
        category: str = "fact",
        source_session: Optional[str] = None,
    ) -> MemoryFact:
        """Add a new fact to memory.

        Args:
            content: The fact content
            category: Category of the fact
            source_session: Session where fact was created

        Returns:
            The created MemoryFact
        """
        if category not in self.CATEGORIES:
            category = "custom"

        fact = MemoryFact.create(content, category, source_session)
        self._facts.append(fact)
        self._save()
        return fact

    def remove_fact(self, fact_id: str) -> bool:
        """Remove a fact by ID.

        Args:
            fact_id: ID of the fact to remove

        Returns:
            True if removed, False if not found
        """
        for i, fact in enumerate(self._facts):
            if fact.fact_id == fact_id:
                self._facts.pop(i)
                self._save()
                return True
        return False

    def update_fact(self, fact_id: str, content: str) -> bool:
        """Update a fact's content.

        Args:
            fact_id: ID of the fact to update
            content: New content

        Returns:
            True if updated, False if not found
        """
        for fact in self._facts:
            if fact.fact_id == fact_id:
                fact.content = content
                fact.keywords = MemoryFact._extract_keywords(content)
                self._save()
                return True
        return False

    def get_all_facts(self) -> List[MemoryFact]:
        """Get all stored facts.

        Returns:
            List of all MemoryFact objects
        """
        return self._facts.copy()

    def get_facts_by_category(self, category: str) -> List[MemoryFact]:
        """Get facts filtered by category.

        Args:
            category: Category to filter by

        Returns:
            List of matching facts
        """
        return [f for f in self._facts if f.category == category]

    def search_facts(self, query: str) -> List[MemoryFact]:
        """Search facts by keyword matching.

        Args:
            query: Search query

        Returns:
            List of matching facts, ordered by relevance
        """
        query_words = set(query.lower().split())
        results = []

        for fact in self._facts:
            # Check keyword overlap
            fact_keywords = set(fact.keywords)
            overlap = len(query_words & fact_keywords)

            # Check if query appears in content
            content_match = query.lower() in fact.content.lower()

            if overlap > 0 or content_match:
                score = overlap + (10 if content_match else 0)
                results.append((fact, score))

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        return [fact for fact, _ in results]

    def get_relevant_facts(self, context: str, limit: int = 5) -> List[MemoryFact]:
        """Get facts relevant to a given context.

        Args:
            context: Current conversation context
            limit: Maximum number of facts to return

        Returns:
            List of relevant facts
        """
        if not context:
            # Return most recent facts
            return sorted(
                self._facts,
                key=lambda f: f.created_at,
                reverse=True
            )[:limit]

        # Use keyword search
        results = self.search_facts(context)
        return results[:limit]

    def build_memory_prompt(self, context: Optional[str] = None) -> str:
        """Build a prompt section for injecting memory.

        Args:
            context: Optional context for relevance filtering

        Returns:
            Memory prompt section or empty string
        """
        if not self._facts:
            return ""

        if context:
            relevant = self.get_relevant_facts(context, limit=10)
        else:
            relevant = self._facts[:10]

        if not relevant:
            return ""

        lines = ["<UserMemory>"]
        lines.append("The following are facts the user has asked you to remember:")

        # Group by category
        by_category: Dict[str, List[str]] = {}
        for fact in relevant:
            if fact.category not in by_category:
                by_category[fact.category] = []
            by_category[fact.category].append(fact.content)

        for category, facts in by_category.items():
            lines.append(f"\n[{category.upper()}]")
            for fact in facts:
                lines.append(f"- {fact}")

        lines.append("</UserMemory>")
        return "\n".join(lines)

    def clear(self) -> None:
        """Clear all stored facts."""
        self._facts.clear()
        self._save()

    def get_fact_count(self) -> int:
        """Get total number of stored facts."""
        return len(self._facts)
