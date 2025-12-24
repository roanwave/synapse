"""Prompt builder for assembling LLM prompts.

This module assembles the final prompt from various components.
It does NOT call LLMs or trigger summarization - it only builds prompts.

Prompt assembly order:
1. SYSTEM PROMPT
2. SUMMARY BLOCK (if context was compressed)
3. RAG CONTEXT (with confidence scores, invisible to user)
4. INTENT SIGNAL (low-priority mode hint)
5. CONVERSATION HISTORY (only non-summarized messages)
6. CURRENT USER MESSAGE
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class Message:
    """A single message in the conversation."""

    role: str  # "user" or "assistant"
    content: str
    index: int = 0  # Position in full history
    is_summarized: bool = False  # Whether this message has been summarized

    def to_dict(self) -> Dict[str, str]:
        """Convert to API-compatible dict format."""
        return {"role": self.role, "content": self.content}


@dataclass
class ConversationHistory:
    """Maintains the conversation history for a session."""

    messages: List[Message] = field(default_factory=list)
    _next_index: int = 0

    def add_user_message(self, content: str) -> Message:
        """Add a user message to the history."""
        msg = Message(role="user", content=content, index=self._next_index)
        self.messages.append(msg)
        self._next_index += 1
        return msg

    def add_assistant_message(self, content: str) -> Message:
        """Add an assistant message to the history."""
        msg = Message(role="assistant", content=content, index=self._next_index)
        self.messages.append(msg)
        self._next_index += 1
        return msg

    def to_api_format(self, include_summarized: bool = False) -> List[Dict[str, str]]:
        """Convert messages to API-compatible format.

        Args:
            include_summarized: Whether to include summarized messages

        Returns:
            List of message dicts
        """
        if include_summarized:
            return [msg.to_dict() for msg in self.messages]
        return [msg.to_dict() for msg in self.messages if not msg.is_summarized]

    def get_active_messages(self) -> List[Message]:
        """Get only non-summarized messages."""
        return [msg for msg in self.messages if not msg.is_summarized]

    def get_summarized_messages(self) -> List[Message]:
        """Get only summarized messages."""
        return [msg for msg in self.messages if msg.is_summarized]

    def mark_summarized(self, up_to_index: int) -> int:
        """Mark messages up to index as summarized.

        Args:
            up_to_index: Mark messages with index <= this as summarized

        Returns:
            Number of messages marked
        """
        count = 0
        for msg in self.messages:
            if msg.index <= up_to_index and not msg.is_summarized:
                msg.is_summarized = True
                count += 1
        return count

    def remove_last_exchange(self) -> Optional[tuple]:
        """Remove the last user-assistant exchange.

        Returns:
            Tuple of (user_message, assistant_message) if removed, None otherwise
        """
        if len(self.messages) < 2:
            return None

        # Check if last two are user-assistant pair
        if (self.messages[-2].role == "user" and
                self.messages[-1].role == "assistant"):
            assistant = self.messages.pop()
            user = self.messages.pop()
            return (user, assistant)

        # Just remove last assistant message if present
        if self.messages[-1].role == "assistant":
            assistant = self.messages.pop()
            if self.messages and self.messages[-1].role == "user":
                user = self.messages[-1]
                return (user, assistant)

        return None

    def get_last_user_message(self) -> Optional[Message]:
        """Get the most recent user message."""
        for msg in reversed(self.messages):
            if msg.role == "user":
                return msg
        return None

    def clear(self) -> None:
        """Clear all messages from history."""
        self.messages.clear()
        self._next_index = 0

    def __len__(self) -> int:
        """Return number of messages."""
        return len(self.messages)


class PromptBuilder:
    """Builds prompts for LLM calls.

    This class is responsible for assembling the final prompt from:
    1. System prompt (base)
    2. Summary block (if context was compressed)
    3. Intent signal (low-priority mode hint)
    4. Conversation history (only non-summarized messages)
    5. Current user message

    Does NOT:
    - Call LLMs
    - Trigger summarization
    - Decide when to summarize
    """

    DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant."

    def __init__(self, system_prompt: Optional[str] = None) -> None:
        """Initialize the prompt builder.

        Args:
            system_prompt: Custom system prompt, or None for default
        """
        self._base_system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        self.history = ConversationHistory()
        self._summary_block: Optional[str] = None
        self._rag_context: Optional[str] = None
        self._rag_chunks: List[Dict[str, Any]] = []  # For inspector
        self._youtube_context: Optional[str] = None
        self._intent_hint: Optional[str] = None

    def set_summary(self, xml_summary: str) -> None:
        """Set the summary block to inject into prompts.

        Args:
            xml_summary: The XML summary content
        """
        if xml_summary:
            self._summary_block = (
                "PREVIOUS CONTEXT HAS BEEN SUMMARIZED AS FOLLOWS:\n\n"
                f"{xml_summary}\n\n"
                "CONTINUE THE CONVERSATION SEAMLESSLY."
            )
        else:
            self._summary_block = None

    def clear_summary(self) -> None:
        """Clear the summary block."""
        self._summary_block = None

    def set_intent_hint(self, hint: str) -> None:
        """Set the intent hint to inject into prompts.

        Args:
            hint: The intent hint string
        """
        self._intent_hint = hint

    def set_rag_context(
        self,
        chunks: List[Dict[str, Any]],
        query: str = "",
    ) -> None:
        """Set RAG context to inject into prompts.

        The context includes confidence scores and metadata visible only
        to the LLM in the system prompt, not to the user.

        Args:
            chunks: List of chunk dicts with content and metadata
            query: The query used for retrieval
        """
        if not chunks:
            self._rag_context = None
            self._rag_chunks = []
            return

        self._rag_chunks = chunks

        # Build RAG context block
        lines = [
            "RELEVANT CONTEXT FROM ATTACHED DOCUMENTS:",
            "(Use this information to inform your response. "
            "Cite sources when directly referencing content.)",
            ""
        ]

        for i, chunk in enumerate(chunks):
            source = chunk.get("source_file", "unknown")
            section = chunk.get("page_or_section", "")
            score = chunk.get("similarity_score", 0)
            content = chunk.get("content", "")

            lines.append(f"[Source {i + 1}: {source}")
            if section:
                lines.append(f" Section: {section}")
            lines.append(f" Relevance: {score:.2f}]")
            lines.append(content)
            lines.append("")

        self._rag_context = "\n".join(lines)

    def clear_rag_context(self) -> None:
        """Clear the RAG context."""
        self._rag_context = None
        self._rag_chunks = []

    def set_youtube_context(self, context_block: str) -> None:
        """Set YouTube transcript context.

        Args:
            context_block: The formatted YouTube transcript block
        """
        self._youtube_context = context_block

    def clear_youtube_context(self) -> None:
        """Clear the YouTube context."""
        self._youtube_context = None

    def get_rag_chunks(self) -> List[Dict[str, Any]]:
        """Get the current RAG chunks for inspection.

        Returns:
            List of chunk dicts with content and metadata
        """
        return self._rag_chunks.copy()

    def build_messages(self) -> List[Dict[str, str]]:
        """Build the messages list for an API call.

        Returns only non-summarized messages.

        Returns:
            List of message dicts ready for the LLM API
        """
        return self.history.to_api_format(include_summarized=False)

    def build_all_messages(self) -> List[Dict[str, str]]:
        """Build all messages including summarized ones.

        Useful for token counting the full history.

        Returns:
            List of all message dicts
        """
        return self.history.to_api_format(include_summarized=True)

    def get_system_prompt(self) -> str:
        """Build the complete system prompt with injections.

        Assembles:
        1. Base system prompt
        2. Summary block (if present)
        3. RAG context (if present)
        4. YouTube context (if present)
        5. Intent hint (if present)

        Returns:
            The complete system prompt string
        """
        parts = [self._base_system_prompt]

        if self._summary_block:
            parts.append("")
            parts.append(self._summary_block)

        if self._rag_context:
            parts.append("")
            parts.append(self._rag_context)

        if self._youtube_context:
            parts.append("")
            parts.append(self._youtube_context)

        if self._intent_hint:
            parts.append("")
            parts.append(self._intent_hint)

        return "\n".join(parts)

    def add_user_message(self, content: str) -> Message:
        """Add a user message to the conversation.

        Args:
            content: The user's message text

        Returns:
            The created Message
        """
        return self.history.add_user_message(content)

    def add_assistant_message(self, content: str) -> Message:
        """Add an assistant response to the conversation.

        Args:
            content: The assistant's response text

        Returns:
            The created Message
        """
        return self.history.add_assistant_message(content)

    def get_message_count(self) -> int:
        """Get the total number of messages in the conversation.

        Returns:
            Number of messages
        """
        return len(self.history)

    def get_active_message_count(self) -> int:
        """Get the number of non-summarized messages.

        Returns:
            Number of active messages
        """
        return len(self.history.get_active_messages())

    def mark_messages_summarized(self, up_to_index: int) -> int:
        """Mark messages as summarized after summarization.

        Args:
            up_to_index: Mark messages up to this index as summarized

        Returns:
            Number of messages marked
        """
        return self.history.mark_summarized(up_to_index)

    def get_messages_for_summarization(
        self,
        boundary_index: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """Get messages that should be summarized.

        Args:
            boundary_index: Optional waypoint boundary

        Returns:
            List of message dicts to summarize
        """
        active = self.history.get_active_messages()

        if boundary_index is not None:
            # Only return messages up to the boundary
            return [
                msg.to_dict() for msg in active
                if msg.index <= boundary_index
            ]

        # Default: return all but the last 4 active messages
        if len(active) <= 4:
            return []

        return [msg.to_dict() for msg in active[:-4]]

    def get_highest_summarizable_index(
        self,
        boundary_index: Optional[int] = None
    ) -> int:
        """Get the highest message index that would be summarized.

        Args:
            boundary_index: Optional waypoint boundary

        Returns:
            The highest index, or -1 if none
        """
        active = self.history.get_active_messages()

        if boundary_index is not None:
            for msg in reversed(active):
                if msg.index <= boundary_index:
                    return msg.index
            return -1

        if len(active) <= 4:
            return -1

        return active[-5].index

    def remove_last_assistant_message(self) -> Optional[str]:
        """Remove the last assistant message for regeneration.

        Returns:
            The removed message content, or None
        """
        result = self.history.remove_last_exchange()
        if result:
            user_msg, assistant_msg = result
            # Re-add the user message (we only wanted to remove assistant)
            self.history.messages.append(user_msg)
            return assistant_msg.content
        return None

    def get_last_user_message(self) -> Optional[str]:
        """Get the most recent user message content.

        Returns:
            The message content, or None
        """
        msg = self.history.get_last_user_message()
        return msg.content if msg else None

    def clear_history(self) -> None:
        """Clear the conversation history, summary, and all context."""
        self.history.clear()
        self._summary_block = None
        self._rag_context = None
        self._rag_chunks = []
        self._youtube_context = None
        self._intent_hint = None
