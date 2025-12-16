"""Anthropic Claude adapter implementation."""

from typing import List, Dict, Any, AsyncIterator

import anthropic

from .base_adapter import LLMAdapter, StreamChunk
from ..config.settings import get_api_key


class AnthropicAdapter(LLMAdapter):
    """Adapter for Anthropic Claude models.

    This adapter is stateless - it receives a prompt and returns a response.
    It does not maintain conversation history or perform any retrieval.
    """

    def __init__(self, model_id: str = "claude-sonnet-4-20250514") -> None:
        """Initialize the Anthropic adapter.

        Args:
            model_id: The Claude model ID to use

        Raises:
            ValueError: If ANTHROPIC_API_KEY is not set
        """
        self._model_id = model_id
        api_key = get_api_key("anthropic")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Please set it to your Anthropic API key."
            )
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    @property
    def model_id(self) -> str:
        """Get the model ID."""
        return self._model_id

    @property
    def provider(self) -> str:
        """Get the provider name."""
        return "anthropic"

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        max_tokens: int = 4096,
    ) -> AsyncIterator[StreamChunk]:
        """Stream a response from Claude.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            system: System prompt
            max_tokens: Maximum tokens to generate

        Yields:
            StreamChunk objects containing response text
        """
        try:
            async with self._client.messages.stream(
                model=self._model_id,
                max_tokens=max_tokens,
                system=system if system else anthropic.NOT_GIVEN,
                messages=messages,
            ) as stream:
                async for text in stream.text_stream:
                    yield StreamChunk(text=text, is_final=False)

                # Get final message for usage stats
                final_message = await stream.get_final_message()
                yield StreamChunk(
                    text="",
                    is_final=True,
                    usage={
                        "input_tokens": final_message.usage.input_tokens,
                        "output_tokens": final_message.usage.output_tokens,
                    },
                )
        except anthropic.APIError as e:
            raise RuntimeError(f"Anthropic API error: {e}") from e

    async def complete(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        max_tokens: int = 4096,
    ) -> str:
        """Get a complete response from Claude.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            system: System prompt
            max_tokens: Maximum tokens to generate

        Returns:
            Complete response text
        """
        try:
            response = await self._client.messages.create(
                model=self._model_id,
                max_tokens=max_tokens,
                system=system if system else anthropic.NOT_GIVEN,
                messages=messages,
            )
            return response.content[0].text
        except anthropic.APIError as e:
            raise RuntimeError(f"Anthropic API error: {e}") from e
