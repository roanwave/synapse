"""Waypoint manager for conversation checkpoints.

Waypoints are invisible markers that users can place to indicate
preferred summarization boundaries. They help preserve important
context when summarization occurs.

Waypoints do NOT:
- Appear in the chat UI (invisible to conversation flow)
- Decide when to summarize (that's context_manager's job)
- Affect the LLM's responses
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class Waypoint:
    """A checkpoint in the conversation."""

    message_index: int  # Index in conversation history
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "index": self.message_index,
            "created_at": self.created_at.isoformat(),
        }


class WaypointManager:
    """Manages conversation waypoints (summarization boundaries).

    Waypoints mark preferred points where summarization should stop.
    When summarization triggers, the system respects the most recent
    waypoint as the cut point if present.

    Responsibilities:
    - Store waypoint indices
    - Provide the most relevant waypoint for summarization
    - Track waypoint metadata

    Does NOT:
    - Decide when to summarize
    - Trigger any actions
    - Appear in the chat UI
    """

    def __init__(self) -> None:
        """Initialize the waypoint manager."""
        self._waypoints: List[Waypoint] = []

    @property
    def waypoints(self) -> List[Waypoint]:
        """Get all waypoints."""
        return self._waypoints.copy()

    @property
    def count(self) -> int:
        """Get the number of waypoints."""
        return len(self._waypoints)

    def add_waypoint(self, message_index: int) -> Waypoint:
        """Add a waypoint at the specified message index.

        Args:
            message_index: The index in conversation history to mark

        Returns:
            The created Waypoint
        """
        # Don't add duplicate waypoints at the same index
        for wp in self._waypoints:
            if wp.message_index == message_index:
                return wp

        waypoint = Waypoint(message_index=message_index)
        self._waypoints.append(waypoint)
        return waypoint

    def remove_waypoint(self, message_index: int) -> bool:
        """Remove a waypoint at the specified index.

        Args:
            message_index: The index to remove waypoint from

        Returns:
            True if a waypoint was removed
        """
        for i, wp in enumerate(self._waypoints):
            if wp.message_index == message_index:
                self._waypoints.pop(i)
                return True
        return False

    def get_summarization_boundary(
        self,
        current_message_count: int,
        min_messages_to_keep: int = 4,
    ) -> Optional[int]:
        """Get the message index where summarization should stop.

        Returns the most recent waypoint that leaves enough messages
        for context, or None if no suitable waypoint exists.

        Args:
            current_message_count: Total number of messages
            min_messages_to_keep: Minimum messages to keep unsummarized

        Returns:
            Message index to stop summarization at, or None
        """
        if not self._waypoints:
            return None

        # Find the most recent waypoint that leaves enough messages
        max_boundary = current_message_count - min_messages_to_keep

        suitable_waypoints = [
            wp for wp in self._waypoints
            if wp.message_index <= max_boundary
        ]

        if not suitable_waypoints:
            return None

        # Return the highest index (most recent) suitable waypoint
        return max(wp.message_index for wp in suitable_waypoints)

    def clear_summarized_waypoints(self, summarized_up_to: int) -> int:
        """Remove waypoints that have been summarized past.

        Args:
            summarized_up_to: Messages up to this index have been summarized

        Returns:
            Number of waypoints removed
        """
        original_count = len(self._waypoints)
        self._waypoints = [
            wp for wp in self._waypoints
            if wp.message_index > summarized_up_to
        ]
        return original_count - len(self._waypoints)

    def adjust_indices(self, removed_count: int) -> None:
        """Adjust waypoint indices after messages are removed.

        Args:
            removed_count: Number of messages that were removed from start
        """
        for wp in self._waypoints:
            wp.message_index = max(0, wp.message_index - removed_count)

    def get_waypoints_for_archive(self) -> List[dict]:
        """Get waypoints in format suitable for conversation archive.

        Returns:
            List of waypoint dictionaries
        """
        return [wp.to_dict() for wp in self._waypoints]

    def clear(self) -> None:
        """Clear all waypoints."""
        self._waypoints.clear()

    def has_waypoint_at(self, message_index: int) -> bool:
        """Check if a waypoint exists at the given index.

        Args:
            message_index: Index to check

        Returns:
            True if waypoint exists at that index
        """
        return any(wp.message_index == message_index for wp in self._waypoints)
