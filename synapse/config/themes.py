"""Dark theme colors and styling for Synapse."""

from dataclasses import dataclass


@dataclass
class ThemeColors:
    """Color scheme for the application."""

    # Base colors
    background: str = "#1a1a2e"
    background_secondary: str = "#16213e"
    background_tertiary: str = "#0f0f1a"

    # Text colors
    text_primary: str = "#e0e0e0"
    text_secondary: str = "#a0a0a0"
    text_muted: str = "#666666"

    # Accent colors
    accent: str = "#4a9eff"
    accent_hover: str = "#6ab0ff"
    accent_pressed: str = "#3a8eef"

    # Message bubble colors
    user_bubble: str = "#2a2a4e"
    assistant_bubble: str = "#1e1e3a"

    # Border and divider
    border: str = "#2a2a4e"
    divider: str = "#2a2a4e"

    # Status colors
    error: str = "#ff6b6b"
    warning: str = "#ffa94d"
    success: str = "#69db7c"

    # Scrollbar
    scrollbar_bg: str = "#1a1a2e"
    scrollbar_handle: str = "#3a3a5e"
    scrollbar_handle_hover: str = "#4a4a6e"


# Global theme instance
theme = ThemeColors()


def get_stylesheet() -> str:
    """Generate the complete application stylesheet.

    Returns:
        CSS stylesheet string for Qt
    """
    return f"""
        QMainWindow {{
            background-color: {theme.background};
        }}

        QWidget {{
            background-color: {theme.background};
            color: {theme.text_primary};
            font-family: "Segoe UI", sans-serif;
            font-size: 14px;
        }}

        QScrollArea {{
            background-color: {theme.background};
            border: none;
        }}

        QScrollBar:vertical {{
            background-color: {theme.scrollbar_bg};
            width: 10px;
            margin: 0;
        }}

        QScrollBar::handle:vertical {{
            background-color: {theme.scrollbar_handle};
            min-height: 30px;
            border-radius: 5px;
            margin: 2px;
        }}

        QScrollBar::handle:vertical:hover {{
            background-color: {theme.scrollbar_handle_hover};
        }}

        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0;
        }}

        QScrollBar::add-page:vertical,
        QScrollBar::sub-page:vertical {{
            background: none;
        }}

        QTextEdit {{
            background-color: {theme.background_secondary};
            color: {theme.text_primary};
            border: 1px solid {theme.border};
            border-radius: 8px;
            padding: 10px;
            selection-background-color: {theme.accent};
        }}

        QTextEdit:focus {{
            border-color: {theme.accent};
        }}

        QPushButton {{
            background-color: {theme.accent};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: bold;
        }}

        QPushButton:hover {{
            background-color: {theme.accent_hover};
        }}

        QPushButton:pressed {{
            background-color: {theme.accent_pressed};
        }}

        QPushButton:disabled {{
            background-color: {theme.text_muted};
        }}

        QLabel {{
            background-color: transparent;
            color: {theme.text_primary};
        }}

        QStatusBar {{
            background-color: {theme.background_tertiary};
            color: {theme.text_secondary};
            border-top: 1px solid {theme.border};
        }}
    """
