"""Prompt builder for assembling LLM prompts.

This module assembles the final prompt from various components.
It does NOT call LLMs or trigger summarization - it only builds prompts.
"""

from typing import List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class Message:
    """A single message in the conversation."""

    role: str  # "user" or "assistant"
    content: str

    def to_dict(self) -> Dict[str, str]:
        """Convert to API-compatible dict format."""
        return {"role": self.role, "content": self.content}


@dataclass
class ConversationHistory:
    """Maintains the conversation history for a session."""

    messages: List[Message] = field(default_factory=list)

    def add_user_message(self, content: str) -> None:
        """Add a user message to the history."""
        self.messages.append(Message(role="user", content=content))

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message to the history."""
        self.messages.append(Message(role="assistant", content=content))

    def to_api_format(self) -> List[Dict[str, str]]:
        """Convert all messages to API-compatible format."""
        return [msg.to_dict() for msg in self.messages]

    def clear(self) -> None:
        """Clear all messages from history."""
        self.messages.clear()

    def __len__(self) -> int:
        """Return number of messages."""
        return len(self.messages)


class PromptBuilder:
    """Builds prompts for LLM calls.

    This class is responsible for assembling the final prompt from:
    - System prompt
    - Summary block (if context was compressed) - Phase 2+
    - RAG context (with confidence scores) - Phase 2+
    - Intent signal (low-priority mode hint) - Phase 2+
    - Conversation history
    - Current user message

    For Phase 1, we only use system prompt and conversation history.
    """

    DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant."

    def __init__(self, system_prompt: str | None = None) -> None:
        """Initialize the prompt builder.

        Args:
            system_prompt: Custom system prompt, or None for default
        """
        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        self.history = ConversationHistory()

    def build_messages(self) -> List[Dict[str, str]]:
        """Build the messages list for an API call.

        Returns:
            List of message dicts ready for the LLM API
        """
        return self.history.to_api_format()

    def get_system_prompt(self) -> str:
        """Get the current system prompt.

        Returns:
            The system prompt string
        """
        return self.system_prompt

    def add_user_message(self, content: str) -> None:
        """Add a user message to the conversation.

        Args:
            content: The user's message text
        """
        self.history.add_user_message(content)

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant response to the conversation.

        Args:
            content: The assistant's response text
        """
        self.history.add_assistant_message(content)

    def get_message_count(self) -> int:
        """Get the number of messages in the conversation.

        Returns:
            Number of messages
        """
        return len(self.history)

    def clear_history(self) -> None:
        """Clear the conversation history."""
        self.history.clear()
