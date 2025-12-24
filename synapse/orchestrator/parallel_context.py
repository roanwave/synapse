"""Parallel context manager for side questions.

Manages a separate conversation thread that shares RAG context
but not the main conversation history.
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SideMessage:
    """A message in the side conversation."""

    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SideConversation:
    """A side conversation with its own context."""

    messages: List[SideMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    merged: bool = False

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the side conversation.

        Args:
            role: "user" or "assistant"
            content: Message content
        """
        self.messages.append(SideMessage(role=role, content=content))

    def get_last_user_message(self) -> Optional[str]:
        """Get the last user message.

        Returns:
            Last user message content or None
        """
        for msg in reversed(self.messages):
            if msg.role == "user":
                return msg.content
        return None

    def to_summary(self) -> str:
        """Generate a summary of the side conversation for merging.

        Returns:
            Summary text suitable for injecting into main conversation
        """
        if not self.messages:
            return ""

        # Format as a compact summary
        lines = ["[Side Discussion Summary]"]
        for msg in self.messages:
            prefix = "Q:" if msg.role == "user" else "A:"
            # Truncate long messages
            content = msg.content
            if len(content) > 200:
                content = content[:200] + "..."
            lines.append(f"{prefix} {content}")

        return "\n".join(lines)

    def build_messages(self) -> List[Dict[str, str]]:
        """Build messages list for LLM API.

        Returns:
            List of message dicts with role and content
        """
        return [
            {"role": msg.role, "content": msg.content}
            for msg in self.messages
        ]


class ParallelContextManager:
    """Manages parallel side conversations.

    Side conversations share:
    - RAG context (document retrieval)
    - Model selection

    Side conversations do NOT share:
    - Main conversation history
    - Summarization state
    - Waypoints
    """

    def __init__(self) -> None:
        """Initialize the parallel context manager."""
        self._active_side: Optional[SideConversation] = None
        self._history: List[SideConversation] = []

    def start_side_conversation(self) -> SideConversation:
        """Start a new side conversation.

        Returns:
            New SideConversation instance
        """
        self._active_side = SideConversation()
        return self._active_side

    def get_active_side(self) -> Optional[SideConversation]:
        """Get the currently active side conversation.

        Returns:
            Active SideConversation or None
        """
        return self._active_side

    def end_side_conversation(self, merge: bool = False) -> Optional[str]:
        """End the current side conversation.

        Args:
            merge: Whether to generate merge summary

        Returns:
            Merge summary if merge=True, None otherwise
        """
        if not self._active_side:
            return None

        summary = None
        if merge and self._active_side.messages:
            self._active_side.merged = True
            summary = self._active_side.to_summary()

        # Archive the conversation
        self._history.append(self._active_side)
        self._active_side = None

        return summary

    def add_user_message(self, content: str) -> bool:
        """Add a user message to the active side conversation.

        Args:
            content: Message content

        Returns:
            True if message was added, False if no active side
        """
        if not self._active_side:
            return False
        self._active_side.add_message("user", content)
        return True

    def add_assistant_message(self, content: str) -> bool:
        """Add an assistant message to the active side conversation.

        Args:
            content: Message content

        Returns:
            True if message was added, False if no active side
        """
        if not self._active_side:
            return False
        self._active_side.add_message("assistant", content)
        return True

    def get_side_system_prompt(self, main_context_summary: Optional[str] = None) -> str:
        """Get the system prompt for side conversations.

        Args:
            main_context_summary: Optional summary of main conversation

        Returns:
            System prompt for side questions
        """
        prompt = (
            "You are answering a quick side question. Keep your response focused and concise. "
            "This is a clarification or exploration that may or may not be merged back into "
            "the main conversation."
        )

        if main_context_summary:
            prompt += f"\n\nMain conversation context:\n{main_context_summary}"

        return prompt

    def clear(self) -> None:
        """Clear all side conversation state."""
        self._active_side = None
        self._history.clear()

    def get_history(self) -> List[SideConversation]:
        """Get all archived side conversations.

        Returns:
            List of past side conversations
        """
        return self._history.copy()
