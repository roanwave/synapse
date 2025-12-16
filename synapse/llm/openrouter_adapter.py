"""OpenRouter adapter implementation.

OpenRouter uses an OpenAI-compatible API with a different base URL.
"""

from typing import List, Dict, Any, AsyncIterator

from openai import AsyncOpenAI, APIError

from .base_adapter import LLMAdapter, StreamChunk
from ..config.settings import get_api_key


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterAdapter(LLMAdapter):
    """Adapter for OpenRouter models.

    This adapter is stateless - it receives a prompt and returns a response.
    It does not maintain conversation history or perform any retrieval.

    OpenRouter provides access to various models through an OpenAI-compatible API.
    """

    def __init__(self, model_id: str = "google/gemini-2.5-flash") -> None:
        """Initialize the OpenRouter adapter.

        Args:
            model_id: The OpenRouter model ID to use

        Raises:
            ValueError: If OPENROUTER_API_KEY is not set
        """
        self._model_id = model_id
        api_key = get_api_key("openrouter")
        if not api_key:
            raise ValueError(
                "OPENROUTER_API_KEY environment variable is not set. "
                "Please set it to your OpenRouter API key."
            )
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL,
            default_headers={
                "HTTP-Referer": "https://github.com/roanwave/synapse",
                "X-Title": "Synapse",
            },
        )

    @property
    def model_id(self) -> str:
        """Get the model ID."""
        return self._model_id

    @property
    def provider(self) -> str:
        """Get the provider name."""
        return "openrouter"

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        max_tokens: int = 4096,
    ) -> AsyncIterator[StreamChunk]:
        """Stream a response from OpenRouter.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            system: System prompt
            max_tokens: Maximum tokens to generate

        Yields:
            StreamChunk objects containing response text
        """
        try:
            # Prepare messages with system prompt
            api_messages = []
            if system:
                api_messages.append({"role": "system", "content": system})
            api_messages.extend(messages)

            stream = await self._client.chat.completions.create(
                model=self._model_id,
                messages=api_messages,
                max_tokens=max_tokens,
                stream=True,
            )

            total_tokens = 0
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield StreamChunk(
                        text=chunk.choices[0].delta.content,
                        is_final=False
                    )

                # OpenRouter may include usage in chunks
                if hasattr(chunk, 'usage') and chunk.usage:
                    total_tokens = chunk.usage.total_tokens

            # Final chunk with usage estimate
            yield StreamChunk(
                text="",
                is_final=True,
                usage={
                    "input_tokens": 0,  # OpenRouter doesn't always provide breakdown
                    "output_tokens": total_tokens,
                },
            )

        except APIError as e:
            raise RuntimeError(f"OpenRouter API error: {e}") from e

    async def complete(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        max_tokens: int = 4096,
    ) -> str:
        """Get a complete response from OpenRouter.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            system: System prompt
            max_tokens: Maximum tokens to generate

        Returns:
            Complete response text
        """
        try:
            # Prepare messages with system prompt
            api_messages = []
            if system:
                api_messages.append({"role": "system", "content": system})
            api_messages.extend(messages)

            response = await self._client.chat.completions.create(
                model=self._model_id,
                messages=api_messages,
                max_tokens=max_tokens,
            )

            return response.choices[0].message.content or ""

        except APIError as e:
            raise RuntimeError(f"OpenRouter API error: {e}") from e
