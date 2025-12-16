"""Context manager for token tracking and summarization triggers.

This module tracks token counts and detects when summarization should occur.
It does NOT generate summaries or call LLMs directly.
"""

from dataclasses import dataclass, field
from typing import Callable, List, Optional
from enum import Enum


class ContextState(Enum):
    """Current state of the context budget."""

    NORMAL = "normal"  # Under 60% of context
    WARNING = "warning"  # 60-80% of context
    CRITICAL = "critical"  # Over 80% of context


@dataclass
class ContextStatus:
    """Current context status information."""

    current_tokens: int
    context_window: int
    percentage: float
    state: ContextState
    summarized_message_count: int
    active_message_count: int


class ContextManager:
    """Manages context window budget and summarization triggers.

    Responsibilities:
    - Track current token count against model's context window
    - Detect when conversation reaches threshold (default 80%)
    - Emit callbacks when summarization should trigger
    - Track which messages have been summarized vs. active

    Does NOT:
    - Generate summaries
    - Call LLMs directly
    - Modify conversation history
    """

    def __init__(
        self,
        context_window: int,
        threshold: float = 0.80,
        warning_threshold: float = 0.60,
    ) -> None:
        """Initialize the context manager.

        Args:
            context_window: Maximum tokens for the current model
            threshold: Percentage at which to trigger summarization (default 80%)
            warning_threshold: Percentage at which to show warning (default 60%)
        """
        self._context_window = context_window
        self._threshold = threshold
        self._warning_threshold = warning_threshold
        self._current_tokens = 0
        self._summarized_count = 0  # Number of messages that have been summarized
        self._total_message_count = 0
        self._on_summarize_callbacks: List[Callable[[], None]] = []
        self._drift_signal_received = False

    @property
    def context_window(self) -> int:
        """Get the context window size."""
        return self._context_window

    @context_window.setter
    def context_window(self, value: int) -> None:
        """Set the context window size (e.g., when switching models)."""
        self._context_window = value

    @property
    def threshold(self) -> float:
        """Get the summarization threshold."""
        return self._threshold

    @threshold.setter
    def threshold(self, value: float) -> None:
        """Set the summarization threshold."""
        self._threshold = max(0.1, min(1.0, value))

    @property
    def current_tokens(self) -> int:
        """Get the current token count."""
        return self._current_tokens

    @property
    def percentage_used(self) -> float:
        """Get the percentage of context window used."""
        if self._context_window == 0:
            return 0.0
        return self._current_tokens / self._context_window

    @property
    def state(self) -> ContextState:
        """Get the current context state."""
        pct = self.percentage_used
        if pct >= self._threshold:
            return ContextState.CRITICAL
        elif pct >= self._warning_threshold:
            return ContextState.WARNING
        return ContextState.NORMAL

    def update_token_count(self, tokens: int) -> bool:
        """Update the current token count.

        Args:
            tokens: New total token count

        Returns:
            True if summarization should be triggered
        """
        self._current_tokens = tokens
        should_summarize = self._should_trigger_summarization()

        if should_summarize:
            self._notify_summarization()

        return should_summarize

    def update_message_counts(
        self,
        total_messages: int,
        summarized_messages: int = 0
    ) -> None:
        """Update message tracking counts.

        Args:
            total_messages: Total number of messages in conversation
            summarized_messages: Number of messages that have been summarized
        """
        self._total_message_count = total_messages
        self._summarized_count = summarized_messages

    def signal_drift_detected(self) -> bool:
        """Signal that semantic drift was detected.

        Returns:
            True if summarization should be triggered due to drift
        """
        self._drift_signal_received = True
        # Drift alone triggers summarization if we're in warning state
        if self.state in (ContextState.WARNING, ContextState.CRITICAL):
            self._notify_summarization()
            return True
        return False

    def clear_drift_signal(self) -> None:
        """Clear the drift signal after it's been handled."""
        self._drift_signal_received = False

    def on_summarize(self, callback: Callable[[], None]) -> None:
        """Register a callback for when summarization should occur.

        Args:
            callback: Function to call when summarization is needed
        """
        self._on_summarize_callbacks.append(callback)

    def get_status(self) -> ContextStatus:
        """Get the current context status.

        Returns:
            ContextStatus with current information
        """
        return ContextStatus(
            current_tokens=self._current_tokens,
            context_window=self._context_window,
            percentage=self.percentage_used,
            state=self.state,
            summarized_message_count=self._summarized_count,
            active_message_count=self._total_message_count - self._summarized_count,
        )

    def mark_messages_summarized(self, count: int) -> None:
        """Mark a number of messages as having been summarized.

        Args:
            count: Number of messages that were summarized
        """
        self._summarized_count = count
        self._drift_signal_received = False

    def reset(self) -> None:
        """Reset the context manager state."""
        self._current_tokens = 0
        self._summarized_count = 0
        self._total_message_count = 0
        self._drift_signal_received = False

    def _should_trigger_summarization(self) -> bool:
        """Check if summarization should be triggered.

        Returns:
            True if summarization conditions are met
        """
        # Don't trigger if we've already summarized all messages
        active_messages = self._total_message_count - self._summarized_count
        if active_messages < 4:  # Need at least some messages to summarize
            return False

        # Trigger on critical threshold
        if self.state == ContextState.CRITICAL:
            return True

        # Trigger on drift + warning state
        if self._drift_signal_received and self.state == ContextState.WARNING:
            return True

        return False

    def _notify_summarization(self) -> None:
        """Notify all registered callbacks that summarization is needed."""
        for callback in self._on_summarize_callbacks:
            callback()
