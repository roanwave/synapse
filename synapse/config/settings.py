"""Application settings and configuration."""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


# Load environment variables from .env file if present
load_dotenv()


@dataclass
class AppSettings:
    """Application-wide settings."""

    # Window defaults
    window_width: int = 1000
    window_height: int = 700
    window_title: str = "Synapse"

    # Default model
    default_model: str = "claude-sonnet-4-20250514"

    # Paths
    app_data_dir: Path = Path.home() / ".synapse"
    logs_dir: Path = Path.home() / ".synapse" / "logs"

    def __post_init__(self) -> None:
        """Ensure directories exist."""
        self.app_data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)


@dataclass
class ModelConfig:
    """Configuration for a specific model."""

    model_id: str
    display_name: str
    context_window: int
    max_output_tokens: int
    provider: str


# Model definitions
MODELS = {
    "claude-sonnet-4-20250514": ModelConfig(
        model_id="claude-sonnet-4-20250514",
        display_name="Claude Sonnet 4",
        context_window=200000,
        max_output_tokens=16384,
        provider="anthropic",
    ),
}


def get_api_key(provider: str) -> Optional[str]:
    """Get API key for a provider from environment variables.

    Args:
        provider: The provider name (anthropic, openai, openrouter)

    Returns:
        The API key if found, None otherwise
    """
    key_map = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
    }
    env_var = key_map.get(provider.lower())
    if env_var:
        return os.getenv(env_var)
    return None


# Global settings instance
settings = AppSettings()
