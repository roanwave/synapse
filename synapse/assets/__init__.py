"""Synapse application assets.

This package contains application resources like icons and images.
"""

from pathlib import Path

# Asset paths
ASSETS_DIR = Path(__file__).parent
ICON_PATH = ASSETS_DIR / "synapse.ico"
ICON_PNG_PATH = ASSETS_DIR / "synapse.png"


def get_icon_path() -> Path:
    """Get the path to the application icon.

    Returns:
        Path to synapse.ico
    """
    return ICON_PATH
