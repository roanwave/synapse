"""Intent tracker for inferring user interaction mode.

This module uses keyword heuristics to infer the user's current mode.
Intent signals affect ONLY tone, verbosity, and reasoning depth.
They MUST NEVER affect retrieval, document selection, or summarization.
"""

import re
from enum import Enum
from dataclasses import dataclass
from typing import List, Set


class IntentMode(Enum):
    """User interaction modes."""

    EXPLORATION = "exploration"  # Default - open-ended, brainstorming
    ANALYSIS = "analysis"  # Questions, explanations, "why/how"
    DRAFTING = "drafting"  # Creating content, writing
    ADVERSARIAL = "adversarial"  # Challenging, arguing, critiquing


@dataclass
class IntentSignal:
    """An intent signal with confidence score."""

    mode: IntentMode
    confidence: float  # 0.0 to 1.0
    keywords_matched: List[str]


# Keyword patterns for each mode
ANALYSIS_PATTERNS: Set[str] = {
    "explain", "why", "how does", "what is", "what are",
    "analyze", "analysis", "understand", "clarify",
    "meaning", "reason", "cause", "effect", "compare",
    "difference", "between", "relationship", "tell me about",
    "describe", "elaborate", "break down", "walk me through",
}

DRAFTING_PATTERNS: Set[str] = {
    "write", "create", "draft", "compose", "generate",
    "make", "build", "produce", "design", "outline",
    "summarize", "rewrite", "edit", "revise", "format",
    "help me write", "can you write", "i need a",
}

ADVERSARIAL_PATTERNS: Set[str] = {
    "challenge", "argue against", "what's wrong",
    "critique", "criticize", "flaw", "weakness",
    "devil's advocate", "counterargument", "refute",
    "disagree", "problem with", "issue with",
    "steelman", "strongest argument against",
}

EXPLORATION_PATTERNS: Set[str] = {
    "what if", "imagine", "brainstorm", "explore",
    "possibilities", "ideas", "think about", "consider",
    "options", "alternatives", "creative", "novel",
    "hypothetical", "scenario", "could we", "might",
}


class IntentTracker:
    """Tracks and infers user intent from message patterns.

    Uses keyword heuristics to determine the user's current mode.
    Mode decays toward 'exploration' (default) over time if no strong signals.

    CONSTRAINT: Intent signals affect ONLY tone, verbosity, and reasoning depth.
    They MUST NEVER affect:
    - Retrieval scope or ranking
    - Document selection
    - Summarization triggers or boundaries
    - RAG chunk filtering
    """

    def __init__(self, decay_rate: float = 0.3) -> None:
        """Initialize the intent tracker.

        Args:
            decay_rate: How much confidence decays each turn without reinforcement
        """
        self._current_mode = IntentMode.EXPLORATION
        self._confidence = 0.5  # Start with moderate confidence in default
        self._decay_rate = decay_rate
        self._recent_signals: List[IntentSignal] = []

    @property
    def current_mode(self) -> IntentMode:
        """Get the current inferred mode."""
        return self._current_mode

    @property
    def confidence(self) -> float:
        """Get confidence in the current mode."""
        return self._confidence

    def update(self, message: str) -> IntentSignal:
        """Update intent based on a new user message.

        Args:
            message: The user's message text

        Returns:
            The detected IntentSignal
        """
        # Apply decay first
        self._apply_decay()

        # Detect signals in the message
        signal = self._detect_intent(message)

        # Update state if we have a strong signal
        if signal.confidence > 0.3:
            self._recent_signals.append(signal)
            # Keep only last 5 signals
            self._recent_signals = self._recent_signals[-5:]

            # If new signal is stronger, switch modes
            if signal.confidence > self._confidence or signal.mode != self._current_mode:
                if signal.confidence >= 0.5:
                    self._current_mode = signal.mode
                    self._confidence = signal.confidence

        return signal

    def get_prompt_hint(self) -> str:
        """Get a subtle hint for the system prompt.

        Returns:
            A low-priority mode hint string
        """
        mode_descriptions = {
            IntentMode.EXPLORATION: "open exploration and brainstorming",
            IntentMode.ANALYSIS: "careful analysis and explanation",
            IntentMode.DRAFTING: "content creation and drafting",
            IntentMode.ADVERSARIAL: "critical examination and challenge",
        }

        description = mode_descriptions.get(
            self._current_mode,
            "open exploration"
        )

        return (
            f"[Current interaction mode appears to be: {description}. "
            f"Adjust tone and depth accordingly.]"
        )

    def reset(self) -> None:
        """Reset to default state."""
        self._current_mode = IntentMode.EXPLORATION
        self._confidence = 0.5
        self._recent_signals.clear()

    def _apply_decay(self) -> None:
        """Apply decay toward exploration mode."""
        if self._current_mode != IntentMode.EXPLORATION:
            self._confidence -= self._decay_rate
            if self._confidence < 0.3:
                self._current_mode = IntentMode.EXPLORATION
                self._confidence = 0.5

    def _detect_intent(self, message: str) -> IntentSignal:
        """Detect intent from message content.

        Args:
            message: The user's message

        Returns:
            IntentSignal with detected mode and confidence
        """
        message_lower = message.lower()

        # Count matches for each mode
        analysis_matches = self._count_pattern_matches(message_lower, ANALYSIS_PATTERNS)
        drafting_matches = self._count_pattern_matches(message_lower, DRAFTING_PATTERNS)
        adversarial_matches = self._count_pattern_matches(message_lower, ADVERSARIAL_PATTERNS)
        exploration_matches = self._count_pattern_matches(message_lower, EXPLORATION_PATTERNS)

        # Find the mode with most matches
        scores = {
            IntentMode.ANALYSIS: analysis_matches,
            IntentMode.DRAFTING: drafting_matches,
            IntentMode.ADVERSARIAL: adversarial_matches,
            IntentMode.EXPLORATION: exploration_matches,
        }

        best_mode = max(scores, key=lambda m: len(scores[m]))
        best_matches = scores[best_mode]

        # Calculate confidence based on match count and message length
        word_count = len(message.split())
        match_count = len(best_matches)

        if match_count == 0:
            # No strong signal, default to exploration with low confidence
            return IntentSignal(
                mode=IntentMode.EXPLORATION,
                confidence=0.2,
                keywords_matched=[],
            )

        # More matches = higher confidence, but cap it
        confidence = min(0.9, 0.3 + (match_count * 0.2))

        # Boost confidence for short, focused messages
        if word_count < 20 and match_count >= 1:
            confidence = min(0.9, confidence + 0.1)

        return IntentSignal(
            mode=best_mode,
            confidence=confidence,
            keywords_matched=list(best_matches),
        )

    def _count_pattern_matches(
        self,
        text: str,
        patterns: Set[str]
    ) -> List[str]:
        """Count how many patterns match in the text.

        Args:
            text: Text to search (should be lowercase)
            patterns: Set of patterns to look for

        Returns:
            List of matched patterns
        """
        matches = []
        for pattern in patterns:
            if pattern in text:
                matches.append(pattern)
        return matches
