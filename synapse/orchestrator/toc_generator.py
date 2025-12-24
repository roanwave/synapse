"""Table of Contents generator for conversations.

Extracts structure from messages to build a navigable TOC.
"""

import re
from typing import List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TOCEntry:
    """A single entry in the table of contents."""

    id: str  # Unique identifier for scrolling
    title: str  # Display title
    message_index: int  # Index of the message
    level: int = 1  # Hierarchy level (1 = top, 2 = sub)
    entry_type: str = "auto"  # "auto", "waypoint", "heading"
    timestamp: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "message_index": self.message_index,
            "level": self.level,
            "entry_type": self.entry_type,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class TOCGenerator:
    """Generates table of contents from conversation messages.

    Extracts structure by detecting:
    - Explicit headings (# Heading)
    - Topic shifts (semantic changes)
    - User waypoints
    - Question patterns
    """

    def __init__(self) -> None:
        """Initialize the TOC generator."""
        self._entries: List[TOCEntry] = []
        self._waypoints: List[int] = []  # Message indices with waypoints

    def add_waypoint(self, message_index: int, title: Optional[str] = None) -> TOCEntry:
        """Add a manual waypoint to the TOC.

        Args:
            message_index: Index of the message
            title: Optional custom title

        Returns:
            The created TOC entry
        """
        self._waypoints.append(message_index)
        entry = TOCEntry(
            id=f"waypoint-{message_index}",
            title=title or f"Waypoint {len(self._waypoints)}",
            message_index=message_index,
            level=1,
            entry_type="waypoint",
            timestamp=datetime.now(),
        )
        self._entries.append(entry)
        self._sort_entries()
        return entry

    def remove_waypoint(self, message_index: int) -> bool:
        """Remove a waypoint from the TOC.

        Args:
            message_index: Index of the message

        Returns:
            True if removed, False if not found
        """
        if message_index in self._waypoints:
            self._waypoints.remove(message_index)
            self._entries = [e for e in self._entries if e.message_index != message_index or e.entry_type != "waypoint"]
            return True
        return False

    def analyze_message(self, message: str, role: str, index: int) -> Optional[TOCEntry]:
        """Analyze a message and potentially add it to the TOC.

        Args:
            message: The message content
            role: "user" or "assistant"
            index: Message index

        Returns:
            TOCEntry if message warrants TOC entry, None otherwise
        """
        entry = None

        # Check for explicit headings in the message
        heading = self._extract_heading(message)
        if heading:
            entry = TOCEntry(
                id=f"heading-{index}",
                title=heading,
                message_index=index,
                level=1,
                entry_type="heading",
                timestamp=datetime.now(),
            )

        # Check for question patterns in user messages
        elif role == "user" and self._is_significant_question(message):
            # Extract a short title from the question
            title = self._extract_question_title(message)
            if title:
                entry = TOCEntry(
                    id=f"question-{index}",
                    title=title,
                    message_index=index,
                    level=2,
                    entry_type="auto",
                    timestamp=datetime.now(),
                )

        # Check for topic indicators in assistant responses
        elif role == "assistant":
            topic = self._extract_topic_indicator(message)
            if topic:
                entry = TOCEntry(
                    id=f"topic-{index}",
                    title=topic,
                    message_index=index,
                    level=1,
                    entry_type="auto",
                    timestamp=datetime.now(),
                )

        if entry:
            self._entries.append(entry)
            self._sort_entries()

        return entry

    def _extract_heading(self, message: str) -> Optional[str]:
        """Extract markdown heading from message.

        Args:
            message: The message content

        Returns:
            Heading text or None
        """
        # Match markdown headings (# Heading)
        match = re.search(r'^#+\s+(.+)$', message, re.MULTILINE)
        if match:
            return match.group(1).strip()[:50]
        return None

    def _is_significant_question(self, message: str) -> bool:
        """Check if message is a significant question worth TOC entry.

        Args:
            message: The message content

        Returns:
            True if significant question
        """
        # Skip very short messages
        if len(message) < 20:
            return False

        # Check for question patterns
        question_patterns = [
            r'\?$',  # Ends with question mark
            r'^(how|what|why|when|where|can|could|would|should|is|are|do|does)\s',
            r'^explain\s',
            r'^tell me about\s',
            r'^describe\s',
        ]

        message_lower = message.lower().strip()
        for pattern in question_patterns:
            if re.search(pattern, message_lower, re.IGNORECASE):
                return True

        return False

    def _extract_question_title(self, message: str) -> Optional[str]:
        """Extract a short title from a question.

        Args:
            message: The question message

        Returns:
            Short title or None
        """
        # Get first line or first sentence
        first_line = message.split('\n')[0].strip()

        # Truncate if too long
        if len(first_line) > 60:
            # Try to break at a word boundary
            truncated = first_line[:57]
            last_space = truncated.rfind(' ')
            if last_space > 30:
                truncated = truncated[:last_space]
            return truncated + "..."

        return first_line if first_line else None

    def _extract_topic_indicator(self, message: str) -> Optional[str]:
        """Extract topic indicator from assistant response.

        Args:
            message: The assistant's message

        Returns:
            Topic title or None
        """
        # Look for explicit topic markers
        patterns = [
            r'^##?\s+(.+)$',  # Markdown heading
            r"^(?:let's|let me|i'll|i will)\s+(?:discuss|explain|cover|talk about)\s+(.+?)[\.\n]",
            r'^(?:topic|section|part):\s*(.+)$',
        ]

        for pattern in patterns:
            match = re.search(pattern, message, re.MULTILINE | re.IGNORECASE)
            if match:
                return match.group(1).strip()[:50]

        return None

    def get_entries(self) -> List[TOCEntry]:
        """Get all TOC entries.

        Returns:
            List of TOC entries sorted by message index
        """
        return self._entries.copy()

    def get_current_section(self, message_index: int) -> Optional[TOCEntry]:
        """Get the TOC entry for the current section.

        Args:
            message_index: Current message index

        Returns:
            The TOC entry for the section containing this message
        """
        current = None
        for entry in self._entries:
            if entry.message_index <= message_index:
                current = entry
            else:
                break
        return current

    def _sort_entries(self) -> None:
        """Sort entries by message index."""
        self._entries.sort(key=lambda e: e.message_index)

    def clear(self) -> None:
        """Clear all entries."""
        self._entries.clear()
        self._waypoints.clear()

    def rebuild_from_messages(self, messages: List[dict]) -> List[TOCEntry]:
        """Rebuild TOC from a list of messages.

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            List of generated TOC entries
        """
        # Keep waypoints, clear auto-generated entries
        waypoint_indices = self._waypoints.copy()
        waypoint_entries = [e for e in self._entries if e.entry_type == "waypoint"]

        self._entries.clear()
        self._entries.extend(waypoint_entries)
        self._waypoints = waypoint_indices

        for i, msg in enumerate(messages):
            role = msg.get("role", "user")
            content = msg.get("content", "")
            self.analyze_message(content, role, i)

        return self._entries.copy()
