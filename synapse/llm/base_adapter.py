"""Base adapter interface for LLM providers."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncIterator
from dataclasses import dataclass


@dataclass
class StreamChunk:
    """A chunk of streamed response."""

    text: str
    is_final: bool = False
    usage: Dict[str, int] | None = None


class LLMAdapter(ABC):
    """Abstract base class for LLM adapters.

    LLM adapters are stateless - they receive a prompt and return a response.
    They do not maintain conversation history or perform retrieval.
    """

    @abstractmethod
    async def stream(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        max_tokens: int = 4096,
    ) -> AsyncIterator[StreamChunk]:
        """Stream a response from the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            system: System prompt
            max_tokens: Maximum tokens to generate

        Yields:
            StreamChunk objects containing response text
        """
        pass

    @abstractmethod
    async def complete(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        max_tokens: int = 4096,
    ) -> str:
        """Get a complete response from the LLM (non-streaming).

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            system: System prompt
            max_tokens: Maximum tokens to generate

        Returns:
            Complete response text
        """
        pass

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Get the model ID."""
        pass

    @property
    @abstractmethod
    def provider(self) -> str:
        """Get the provider name."""
        pass
