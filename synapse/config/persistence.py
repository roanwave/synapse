"""Settings persistence for Synapse.

Saves and loads user preferences and window state to ~/.synapse/config.json
"""

import json
from typing import Optional, Dict, Any, List
from pathlib import Path
from dataclasses import dataclass, field, asdict

from .settings import settings


@dataclass
class WindowState:
    """Window position and size state."""

    x: int = 100
    y: int = 100
    width: int = 1000
    height: int = 700
    maximized: bool = False


@dataclass
class UserPreferences:
    """User preferences that persist between sessions."""

    # Last used model
    last_model: str = "claude-sonnet-4-5-20250929"

    # Window state
    window: WindowState = field(default_factory=WindowState)

    # UI state
    focus_mode: bool = False
    inspector_visible: bool = False

    # Default artifact generation options
    generate_outline: bool = True
    generate_decisions: bool = True
    generate_research: bool = False

    # Keyboard shortcuts reminder shown
    shortcuts_shown: bool = False

    # Crucible integration settings
    crucible_enabled: bool = False
    crucible_router: str = "Auto"  # "Auto", "Custom-Role", or "Custom-Cost"


class PersistenceManager:
    """Manages saving and loading user preferences."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        """Initialize the persistence manager.

        Args:
            config_path: Path to config file, defaults to ~/.synapse/config.json
        """
        self._config_path = config_path or (settings.app_data_dir / "config.json")
        self._preferences: Optional[UserPreferences] = None

    @property
    def preferences(self) -> UserPreferences:
        """Get current preferences, loading from disk if needed."""
        if self._preferences is None:
            self._preferences = self.load()
        return self._preferences

    def load(self) -> UserPreferences:
        """Load preferences from disk.

        Returns:
            UserPreferences instance (defaults if file doesn't exist)
        """
        if not self._config_path.exists():
            return UserPreferences()

        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return self._dict_to_preferences(data)
        except (json.JSONDecodeError, KeyError, TypeError):
            # If loading fails, return defaults
            return UserPreferences()

    def save(self, preferences: Optional[UserPreferences] = None) -> None:
        """Save preferences to disk.

        Args:
            preferences: Preferences to save, or current if None
        """
        if preferences is not None:
            self._preferences = preferences

        if self._preferences is None:
            return

        # Ensure directory exists
        self._config_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict
        data = self._preferences_to_dict(self._preferences)

        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def update_window_state(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        maximized: bool = False,
    ) -> None:
        """Update window state and save.

        Args:
            x: Window X position
            y: Window Y position
            width: Window width
            height: Window height
            maximized: Whether window is maximized
        """
        prefs = self.preferences
        prefs.window.x = x
        prefs.window.y = y
        prefs.window.width = width
        prefs.window.height = height
        prefs.window.maximized = maximized
        self.save()

    def update_last_model(self, model_id: str) -> None:
        """Update last used model and save.

        Args:
            model_id: The model ID
        """
        prefs = self.preferences
        prefs.last_model = model_id
        self.save()

    def update_focus_mode(self, enabled: bool) -> None:
        """Update focus mode state and save.

        Args:
            enabled: Whether focus mode is enabled
        """
        prefs = self.preferences
        prefs.focus_mode = enabled
        self.save()

    def update_inspector_visible(self, visible: bool) -> None:
        """Update inspector visibility and save.

        Args:
            visible: Whether inspector is visible
        """
        prefs = self.preferences
        prefs.inspector_visible = visible
        self.save()

    def update_artifact_options(
        self,
        outline: bool,
        decisions: bool,
        research: bool,
    ) -> None:
        """Update default artifact generation options and save.

        Args:
            outline: Generate conversation outline
            decisions: Generate decision log
            research: Generate research index
        """
        prefs = self.preferences
        prefs.generate_outline = outline
        prefs.generate_decisions = decisions
        prefs.generate_research = research
        self.save()

    def update_crucible_settings(
        self,
        enabled: bool,
        router: str,
    ) -> None:
        """Update Crucible integration settings and save.

        Args:
            enabled: Whether Crucible is enabled
            router: Router mode ("Auto", "Custom-Role", or "Custom-Cost")
        """
        prefs = self.preferences
        prefs.crucible_enabled = enabled
        prefs.crucible_router = router
        self.save()

    def _preferences_to_dict(self, prefs: UserPreferences) -> Dict[str, Any]:
        """Convert preferences to dictionary.

        Args:
            prefs: UserPreferences instance

        Returns:
            Dictionary representation
        """
        return {
            "last_model": prefs.last_model,
            "window": {
                "x": prefs.window.x,
                "y": prefs.window.y,
                "width": prefs.window.width,
                "height": prefs.window.height,
                "maximized": prefs.window.maximized,
            },
            "focus_mode": prefs.focus_mode,
            "inspector_visible": prefs.inspector_visible,
            "generate_outline": prefs.generate_outline,
            "generate_decisions": prefs.generate_decisions,
            "generate_research": prefs.generate_research,
            "shortcuts_shown": prefs.shortcuts_shown,
            "crucible_enabled": prefs.crucible_enabled,
            "crucible_router": prefs.crucible_router,
        }

    def _dict_to_preferences(self, data: Dict[str, Any]) -> UserPreferences:
        """Convert dictionary to preferences.

        Args:
            data: Dictionary from JSON

        Returns:
            UserPreferences instance
        """
        window_data = data.get("window", {})
        window = WindowState(
            x=window_data.get("x", 100),
            y=window_data.get("y", 100),
            width=window_data.get("width", 1000),
            height=window_data.get("height", 700),
            maximized=window_data.get("maximized", False),
        )

        return UserPreferences(
            last_model=data.get("last_model", "claude-sonnet-4-5-20250929"),
            window=window,
            focus_mode=data.get("focus_mode", False),
            inspector_visible=data.get("inspector_visible", False),
            generate_outline=data.get("generate_outline", True),
            generate_decisions=data.get("generate_decisions", True),
            generate_research=data.get("generate_research", False),
            shortcuts_shown=data.get("shortcuts_shown", False),
            crucible_enabled=data.get("crucible_enabled", False),
            crucible_router=data.get("crucible_router", "Auto"),
        )


# Global instance
persistence = PersistenceManager()
