"""Model-aware token counting utilities."""

from typing import List, Dict, Any

import tiktoken


class TokenCounter:
    """Counts tokens for different model providers.

    Uses tiktoken for OpenAI models and a character-based approximation
    for Claude and other models (since they don't expose public tokenizers).
    """

    def __init__(self, model_id: str = "claude-sonnet-4-5-20250514") -> None:
        """Initialize the token counter.

        Args:
            model_id: The model ID to use for token counting
        """
        self.model_id = model_id
        self._tiktoken_encoder = None

        # Determine provider from model ID
        if model_id.startswith("claude"):
            self.provider = "anthropic"
        elif model_id.startswith("gpt") or model_id.startswith("o1") or model_id.startswith("o3"):
            self.provider = "openai"
            # Try to get encoder, fall back to cl100k_base for newer models
            try:
                self._tiktoken_encoder = tiktoken.encoding_for_model(model_id)
            except KeyError:
                # Use cl100k_base as fallback for GPT-4 class models
                self._tiktoken_encoder = tiktoken.get_encoding("cl100k_base")
        elif "/" in model_id:
            # OpenRouter models have format provider/model
            self.provider = "openrouter"
        else:
            self.provider = "unknown"

    def count_text(self, text: str) -> int:
        """Count tokens in a text string.

        Args:
            text: The text to count tokens for

        Returns:
            Estimated token count
        """
        if not text:
            return 0

        if self.provider == "openai" and self._tiktoken_encoder:
            return len(self._tiktoken_encoder.encode(text))

        # For Claude and other models, use character-based approximation
        # Most tokenizers average ~4 characters per token for English
        return len(text) // 4

    def count_messages(self, messages: List[Dict[str, Any]]) -> int:
        """Count tokens in a list of messages.

        Args:
            messages: List of message dicts with 'role' and 'content' keys

        Returns:
            Total estimated token count
        """
        total = 0
        for message in messages:
            # Count content
            content = message.get("content", "")
            if isinstance(content, str):
                total += self.count_text(content)
            elif isinstance(content, list):
                # Handle multi-part content (e.g., with images)
                for part in content:
                    if isinstance(part, dict) and "text" in part:
                        total += self.count_text(part["text"])

            # Add overhead for message structure (~4 tokens per message)
            total += 4

        return total

    def count_prompt(self, system: str, messages: List[Dict[str, Any]]) -> int:
        """Count total tokens for a complete prompt.

        Args:
            system: System prompt text
            messages: List of conversation messages

        Returns:
            Total estimated token count
        """
        system_tokens = self.count_text(system)
        message_tokens = self.count_messages(messages)
        # Add overhead for prompt structure
        return system_tokens + message_tokens + 10


def create_counter(model_id: str) -> TokenCounter:
    """Factory function to create a token counter for a model.

    Args:
        model_id: The model ID

    Returns:
        Configured TokenCounter instance
    """
    return TokenCounter(model_id)
