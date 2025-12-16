"""Drift detector for semantic shift detection.

This module tracks the semantic centroid of recent conversation and
detects when new messages diverge significantly, indicating a topic shift.

Drift detection can trigger early summarization to preserve context
about the previous topic before it becomes stale.

Does NOT:
- Decide when to summarize (context_manager's job based on drift signals)
- Generate summaries
- Modify conversation history
"""

import re
from collections import Counter
from dataclasses import dataclass
from typing import List, Set, Optional


@dataclass
class DriftResult:
    """Result of drift analysis."""

    is_drift: bool
    similarity: float  # 0.0 to 1.0
    current_keywords: Set[str]
    centroid_keywords: Set[str]


class DriftDetector:
    """Detects semantic drift in conversation.

    Uses keyword-based similarity to track topic coherence.
    When similarity drops below threshold, signals potential drift.

    For Phase 2, uses simple keyword overlap. Future phases could
    use embeddings for more accurate semantic comparison.

    Threshold is configurable in settings.
    """

    # Common stop words to exclude from analysis
    STOP_WORDS: Set[str] = {
        "a", "an", "the", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "must", "shall",
        "can", "to", "of", "in", "for", "on", "with", "at", "by",
        "from", "as", "into", "through", "during", "before", "after",
        "above", "below", "between", "under", "again", "further",
        "then", "once", "here", "there", "when", "where", "why",
        "how", "all", "each", "few", "more", "most", "other", "some",
        "such", "no", "nor", "not", "only", "own", "same", "so",
        "than", "too", "very", "just", "and", "but", "if", "or",
        "because", "until", "while", "about", "against", "this",
        "that", "these", "those", "am", "i", "you", "he", "she",
        "it", "we", "they", "what", "which", "who", "whom", "its",
        "his", "her", "their", "my", "your", "our", "me", "him",
        "them", "us", "also", "get", "got", "make", "made", "like",
        "want", "need", "know", "think", "see", "look", "use",
    }

    def __init__(
        self,
        window_size: int = 6,
        threshold: float = 0.25,
    ) -> None:
        """Initialize the drift detector.

        Args:
            window_size: Number of recent messages to track for centroid
            threshold: Similarity threshold below which drift is detected
        """
        self._window_size = window_size
        self._threshold = threshold
        self._message_keywords: List[Set[str]] = []
        self._centroid: Counter = Counter()

    @property
    def threshold(self) -> float:
        """Get the drift threshold."""
        return self._threshold

    @threshold.setter
    def threshold(self, value: float) -> None:
        """Set the drift threshold."""
        self._threshold = max(0.0, min(1.0, value))

    @property
    def window_size(self) -> int:
        """Get the window size."""
        return self._window_size

    def analyze_message(self, message: str) -> DriftResult:
        """Analyze a message for drift from the conversation centroid.

        Args:
            message: The message text to analyze

        Returns:
            DriftResult with drift detection outcome
        """
        keywords = self._extract_keywords(message)

        # If we don't have enough history, can't detect drift
        if len(self._message_keywords) < 2:
            self._add_to_window(keywords)
            return DriftResult(
                is_drift=False,
                similarity=1.0,
                current_keywords=keywords,
                centroid_keywords=set(self._centroid.keys()),
            )

        # Calculate similarity with centroid
        similarity = self._calculate_similarity(keywords)

        # Detect drift
        is_drift = similarity < self._threshold

        # Update window
        self._add_to_window(keywords)

        return DriftResult(
            is_drift=is_drift,
            similarity=similarity,
            current_keywords=keywords,
            centroid_keywords=set(self._centroid.keys()),
        )

    def _extract_keywords(self, text: str) -> Set[str]:
        """Extract meaningful keywords from text.

        Args:
            text: Text to extract keywords from

        Returns:
            Set of keywords
        """
        # Convert to lowercase and extract words
        words = re.findall(r'\b[a-z]{3,}\b', text.lower())

        # Filter out stop words and keep meaningful terms
        keywords = {
            word for word in words
            if word not in self.STOP_WORDS
        }

        return keywords

    def _calculate_similarity(self, keywords: Set[str]) -> float:
        """Calculate Jaccard-like similarity with centroid.

        Args:
            keywords: Keywords from current message

        Returns:
            Similarity score from 0.0 to 1.0
        """
        if not keywords or not self._centroid:
            return 0.0

        centroid_keywords = set(self._centroid.keys())

        # Weighted overlap - words that appear more in centroid count more
        overlap_score = 0.0
        for word in keywords:
            if word in self._centroid:
                # Weight by frequency in centroid
                overlap_score += min(1.0, self._centroid[word] / 2)

        # Normalize by combined unique words
        union_size = len(keywords | centroid_keywords)
        if union_size == 0:
            return 0.0

        return overlap_score / union_size

    def _add_to_window(self, keywords: Set[str]) -> None:
        """Add keywords to the sliding window and update centroid.

        Args:
            keywords: Keywords to add
        """
        # Add to window
        self._message_keywords.append(keywords)

        # Update centroid with new keywords
        for word in keywords:
            self._centroid[word] += 1

        # Remove oldest if window exceeded
        if len(self._message_keywords) > self._window_size:
            oldest = self._message_keywords.pop(0)
            for word in oldest:
                self._centroid[word] -= 1
                if self._centroid[word] <= 0:
                    del self._centroid[word]

    def get_top_keywords(self, n: int = 10) -> List[str]:
        """Get the top keywords in the current centroid.

        Args:
            n: Number of top keywords to return

        Returns:
            List of top keywords
        """
        return [word for word, _ in self._centroid.most_common(n)]

    def reset(self) -> None:
        """Reset the drift detector state."""
        self._message_keywords.clear()
        self._centroid.clear()

    def force_recalculate_centroid(self, messages: List[str]) -> None:
        """Recalculate centroid from a list of messages.

        Useful after summarization to reset the baseline.

        Args:
            messages: List of message texts
        """
        self.reset()
        for msg in messages[-self._window_size:]:
            keywords = self._extract_keywords(msg)
            self._add_to_window(keywords)
