"""Application settings and configuration."""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


# Find project root (parent of synapse package)
_PROJECT_ROOT = Path(__file__).parent.parent.parent

# Load environment variables from .env file if present
# Check both project root and current working directory
load_dotenv(_PROJECT_ROOT / ".env")
load_dotenv()  # Also check CWD as fallback


@dataclass
class AppSettings:
    """Application-wide settings."""

    # Window defaults
    window_width: int = 1000
    window_height: int = 700
    window_title: str = "Synapse"

    # Default model
    default_model: str = "claude-sonnet-4-5-20250514"

    # Paths
    app_data_dir: Path = Path.home() / ".synapse"
    logs_dir: Path = Path.home() / ".synapse" / "logs"

    def __post_init__(self) -> None:
        """Ensure directories exist."""
        self.app_data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)


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
        "openrouter": "OPENROUTER_KEY",
        "gabai": "GABAI_KEY",
    }
    env_var = key_map.get(provider.lower())
    if env_var:
        return os.getenv(env_var)
    return None


# Global settings instance
settings = AppSettings()
