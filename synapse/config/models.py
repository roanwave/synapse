"""Model definitions for all supported LLM providers."""

from dataclasses import dataclass
from typing import Dict, List, Optional

from .settings import get_api_key


@dataclass
class ModelConfig:
    """Configuration for a specific model."""

    model_id: str
    display_name: str
    provider: str  # anthropic, openai, openrouter
    context_window: int
    max_output_tokens: int


# All supported models
MODELS: Dict[str, ModelConfig] = {
    # Anthropic models
    "claude-opus-4-5-20250514": ModelConfig(
        model_id="claude-opus-4-5-20250514",
        display_name="Claude Opus 4.5",
        provider="anthropic",
        context_window=200000,
        max_output_tokens=32768,
    ),
    "claude-sonnet-4-5-20250514": ModelConfig(
        model_id="claude-sonnet-4-5-20250514",
        display_name="Claude Sonnet 4.5",
        provider="anthropic",
        context_window=200000,
        max_output_tokens=16384,
    ),
    # OpenAI models
    "gpt-4o": ModelConfig(
        model_id="gpt-4o",
        display_name="GPT-4o",
        provider="openai",
        context_window=128000,
        max_output_tokens=16384,
    ),
    "o1": ModelConfig(
        model_id="o1",
        display_name="o1",
        provider="openai",
        context_window=200000,
        max_output_tokens=100000,
    ),
    "o3-mini": ModelConfig(
        model_id="o3-mini",
        display_name="o3-mini",
        provider="openai",
        context_window=200000,
        max_output_tokens=100000,
    ),
    "gpt-5": ModelConfig(
        model_id="gpt-5",
        display_name="GPT-5",
        provider="openai",
        context_window=200000,
        max_output_tokens=32768,
    ),
    "gpt-5.2": ModelConfig(
        model_id="gpt-5.2",
        display_name="GPT-5.2",
        provider="openai",
        context_window=200000,
        max_output_tokens=32768,
    ),
    # OpenRouter models
    "google/gemini-2.5-flash": ModelConfig(
        model_id="google/gemini-2.5-flash",
        display_name="Gemini 2.5 Flash",
        provider="openrouter",
        context_window=1000000,
        max_output_tokens=8192,
    ),
    "google/gemini-2.5-pro": ModelConfig(
        model_id="google/gemini-2.5-pro",
        display_name="Gemini 2.5 Pro",
        provider="openrouter",
        context_window=1000000,
        max_output_tokens=8192,
    ),
    "google/gemini-3-pro-preview": ModelConfig(
        model_id="google/gemini-3-pro-preview",
        display_name="Gemini 3 Pro Preview",
        provider="openrouter",
        context_window=1000000,
        max_output_tokens=16384,
    ),
    "deepseek/deepseek-v3.2": ModelConfig(
        model_id="deepseek/deepseek-v3.2",
        display_name="DeepSeek V3.2",
        provider="openrouter",
        context_window=128000,
        max_output_tokens=8192,
    ),
    "cognitivecomputations/dolphin-mistral-24b-venice-edition:free": ModelConfig(
        model_id="cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
        display_name="Dolphin Mistral 24B (Free)",
        provider="openrouter",
        context_window=32768,
        max_output_tokens=4096,
    ),
}


def get_model(model_id: str) -> Optional[ModelConfig]:
    """Get model configuration by ID.

    Args:
        model_id: The model identifier

    Returns:
        ModelConfig if found, None otherwise
    """
    return MODELS.get(model_id)


def get_models_by_provider(provider: str) -> List[ModelConfig]:
    """Get all models for a specific provider.

    Args:
        provider: Provider name (anthropic, openai, openrouter)

    Returns:
        List of ModelConfig for that provider
    """
    return [m for m in MODELS.values() if m.provider == provider]


def get_available_models() -> List[ModelConfig]:
    """Get all models that have valid API keys configured.

    Returns:
        List of ModelConfig for models with available API keys
    """
    available = []
    for model in MODELS.values():
        if get_api_key(model.provider):
            available.append(model)
    return available


def get_available_providers() -> List[str]:
    """Get providers that have API keys configured.

    Returns:
        List of provider names with valid API keys
    """
    providers = set()
    for provider in ["anthropic", "openai", "openrouter"]:
        if get_api_key(provider):
            providers.add(provider)
    return list(providers)


def is_provider_available(provider: str) -> bool:
    """Check if a provider has an API key configured.

    Args:
        provider: Provider name

    Returns:
        True if API key is available
    """
    return get_api_key(provider) is not None
