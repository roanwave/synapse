"""OpenAI adapter implementation."""

from typing import List, Dict, Any, AsyncIterator

from openai import AsyncOpenAI, APIError

from .base_adapter import LLMAdapter, StreamChunk
from ..config.settings import get_api_key


class OpenAIAdapter(LLMAdapter):
    """Adapter for OpenAI models.

    This adapter is stateless - it receives a prompt and returns a response.
    It does not maintain conversation history or perform any retrieval.
    """

    def __init__(self, model_id: str = "gpt-4o") -> None:
        """Initialize the OpenAI adapter.

        Args:
            model_id: The OpenAI model ID to use

        Raises:
            ValueError: If OPENAI_API_KEY is not set
        """
        self._model_id = model_id
        api_key = get_api_key("openai")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is not set. "
                "Please set it to your OpenAI API key."
            )
        self._client = AsyncOpenAI(api_key=api_key)

    @property
    def model_id(self) -> str:
        """Get the model ID."""
        return self._model_id

    @property
    def provider(self) -> str:
        """Get the provider name."""
        return "openai"

    def _is_reasoning_model(self) -> bool:
        """Check if this is a reasoning model (o1, o3 series)."""
        return self._model_id.startswith("o1") or self._model_id.startswith("o3")

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        max_tokens: int = 4096,
    ) -> AsyncIterator[StreamChunk]:
        """Stream a response from OpenAI.

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

            # Reasoning models (o1, o3) don't support system messages
            # Instead, prepend as a user message
            if self._is_reasoning_model():
                if system:
                    api_messages.append({
                        "role": "user",
                        "content": f"[System Instructions]\n{system}\n[End System Instructions]"
                    })
                    # Add a fake assistant acknowledgment for context
                    api_messages.append({
                        "role": "assistant",
                        "content": "Understood. I'll follow these instructions."
                    })
            else:
                if system:
                    api_messages.append({"role": "system", "content": system})

            api_messages.extend(messages)

            # Reasoning models don't support streaming
            if self._is_reasoning_model():
                response = await self._client.chat.completions.create(
                    model=self._model_id,
                    messages=api_messages,
                    max_completion_tokens=max_tokens,
                )

                content = response.choices[0].message.content or ""
                yield StreamChunk(text=content, is_final=False)

                yield StreamChunk(
                    text="",
                    is_final=True,
                    usage={
                        "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                        "output_tokens": response.usage.completion_tokens if response.usage else 0,
                    },
                )
            else:
                # Standard streaming for non-reasoning models
                # Use max_completion_tokens for newer API compatibility
                stream = await self._client.chat.completions.create(
                    model=self._model_id,
                    messages=api_messages,
                    max_completion_tokens=max_tokens,
                    stream=True,
                    stream_options={"include_usage": True},
                )

                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield StreamChunk(
                            text=chunk.choices[0].delta.content,
                            is_final=False
                        )

                    # Check for usage in final chunk
                    if chunk.usage:
                        yield StreamChunk(
                            text="",
                            is_final=True,
                            usage={
                                "input_tokens": chunk.usage.prompt_tokens,
                                "output_tokens": chunk.usage.completion_tokens,
                            },
                        )

        except APIError as e:
            raise RuntimeError(f"OpenAI API error: {e}") from e

    async def complete(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        max_tokens: int = 4096,
    ) -> str:
        """Get a complete response from OpenAI.

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

            if self._is_reasoning_model():
                if system:
                    api_messages.append({
                        "role": "user",
                        "content": f"[System Instructions]\n{system}\n[End System Instructions]"
                    })
                    api_messages.append({
                        "role": "assistant",
                        "content": "Understood. I'll follow these instructions."
                    })
            else:
                if system:
                    api_messages.append({"role": "system", "content": system})

            api_messages.extend(messages)

            if self._is_reasoning_model():
                response = await self._client.chat.completions.create(
                    model=self._model_id,
                    messages=api_messages,
                    max_completion_tokens=max_tokens,
                )
            else:
                response = await self._client.chat.completions.create(
                    model=self._model_id,
                    messages=api_messages,
                    max_completion_tokens=max_tokens,
                )

            return response.choices[0].message.content or ""

        except APIError as e:
            raise RuntimeError(f"OpenAI API error: {e}") from e
