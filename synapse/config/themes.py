"""Dark theme colors and styling for Synapse.

Premium aesthetic: sleek, minimalist, spacious.
Fonts:
- UI elements: Inter, Roboto (fallback to Segoe UI)
- Chat messages: Segoe UI (Windows native)
- Code/XML: JetBrains Mono, Fira Code (fallback to Consolas)
"""

from dataclasses import dataclass


@dataclass
class ThemeColors:
    """Color scheme for the application.

    Based on VS Code dark theme aesthetic with custom accent.
    """

    # Base colors (Deep Charcoal palette)
    background: str = "#1E1E1E"  # Main background - dark but not true black
    background_secondary: str = "#252526"  # Surface/cards - subtle layering
    background_tertiary: str = "#1A1A1A"  # Deeper areas

    # Text colors
    text_primary: str = "#F0F0F0"  # Near-white for high contrast
    text_secondary: str = "#ABABAB"  # Muted text
    text_muted: str = "#6E6E6E"  # Very muted/disabled text

    # Accent colors (VS Code blue)
    accent: str = "#007ACC"  # Primary accent
    accent_hover: str = "#1A8AD4"  # Lighter on hover
    accent_pressed: str = "#005A9E"  # Darker on press
    accent_subtle: str = "#264F78"  # Very subtle accent

    # Message bubble colors
    user_bubble: str = "#005A8D"  # Dark accent blue for user
    assistant_bubble: str = "#2D2D2D"  # Slightly lighter than background

    # Border and divider (minimal, subtle)
    border: str = "#3C3C3C"  # Subtle border
    border_subtle: str = "#2D2D2D"  # Even more subtle
    divider: str = "#2D2D2D"

    # Status colors
    error: str = "#F14C4C"  # Red
    warning: str = "#CCA700"  # Yellow/Orange
    success: str = "#89D185"  # Green

    # Token budget colors (gradient)
    budget_green: str = "#89D185"
    budget_yellow: str = "#CCA700"
    budget_orange: str = "#CE9178"
    budget_red: str = "#F14C4C"

    # Scrollbar (minimal)
    scrollbar_bg: str = "#1E1E1E"
    scrollbar_handle: str = "#424242"
    scrollbar_handle_hover: str = "#555555"

    # Focus mode indicator
    focus_border: str = "#007ACC"


@dataclass
class ThemeFonts:
    """Font families for different UI contexts."""

    # UI elements (labels, buttons, menus)
    ui: str = "'Inter', 'Roboto', 'Segoe UI', sans-serif"

    # Chat messages (Windows native feel)
    chat: str = "'Segoe UI', 'SF Pro Text', sans-serif"

    # Code and XML display
    mono: str = "'JetBrains Mono', 'Fira Code', 'Consolas', monospace"


@dataclass
class ThemeMetrics:
    """Spacing and sizing constants."""

    # Border radius
    radius_small: int = 4
    radius_medium: int = 6
    radius_large: int = 8

    # Padding
    padding_small: int = 8
    padding_medium: int = 12
    padding_large: int = 16
    padding_xlarge: int = 24

    # Font sizes
    font_small: int = 11
    font_normal: int = 13
    font_medium: int = 14
    font_large: int = 16


# Global instances
theme = ThemeColors()
fonts = ThemeFonts()
metrics = ThemeMetrics()


def get_stylesheet() -> str:
    """Generate the complete application stylesheet.

    Returns:
        CSS stylesheet string for Qt
    """
    return f"""
        /* === GLOBAL === */
        QMainWindow {{
            background-color: {theme.background};
        }}

        QWidget {{
            background-color: {theme.background};
            color: {theme.text_primary};
            font-family: {fonts.ui};
            font-size: {metrics.font_normal}px;
        }}

        /* === SCROLL AREAS === */
        QScrollArea {{
            background-color: {theme.background};
            border: none;
        }}

        QScrollBar:vertical {{
            background-color: {theme.scrollbar_bg};
            width: 8px;
            margin: 0;
            border-radius: 4px;
        }}

        QScrollBar::handle:vertical {{
            background-color: {theme.scrollbar_handle};
            min-height: 30px;
            border-radius: 4px;
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

        /* === TEXT INPUTS === */
        QTextEdit {{
            background-color: {theme.background_secondary};
            color: {theme.text_primary};
            border: 1px solid {theme.border_subtle};
            border-radius: {metrics.radius_medium}px;
            padding: {metrics.padding_medium}px;
            selection-background-color: {theme.accent};
            font-family: {fonts.chat};
            font-size: {metrics.font_medium}px;
        }}

        QTextEdit:focus {{
            border-color: {theme.accent};
        }}

        QTextEdit:disabled {{
            background-color: {theme.background_tertiary};
            color: {theme.text_muted};
        }}

        /* === BUTTONS === */
        QPushButton {{
            background-color: {theme.accent};
            color: white;
            border: none;
            border-radius: {metrics.radius_medium}px;
            padding: {metrics.padding_small}px {metrics.padding_medium}px;
            font-weight: 500;
            font-family: {fonts.ui};
        }}

        QPushButton:hover {{
            background-color: {theme.accent_hover};
        }}

        QPushButton:pressed {{
            background-color: {theme.accent_pressed};
        }}

        QPushButton:disabled {{
            background-color: {theme.border};
            color: {theme.text_muted};
        }}

        /* === LABELS === */
        QLabel {{
            background-color: transparent;
            color: {theme.text_primary};
            font-family: {fonts.ui};
        }}

        /* === STATUS BAR === */
        QStatusBar {{
            background-color: {theme.background_tertiary};
            color: {theme.text_secondary};
            border-top: 1px solid {theme.border_subtle};
            font-size: {metrics.font_small}px;
        }}

        /* === COMBO BOX === */
        QComboBox {{
            background-color: {theme.background_secondary};
            color: {theme.text_primary};
            border: 1px solid {theme.border_subtle};
            border-radius: {metrics.radius_medium}px;
            padding: {metrics.padding_small}px {metrics.padding_medium}px;
            min-height: 20px;
            font-family: {fonts.ui};
        }}

        QComboBox:hover {{
            border-color: {theme.border};
        }}

        QComboBox:focus {{
            border-color: {theme.accent};
        }}

        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}

        QComboBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid {theme.text_secondary};
            margin-right: 8px;
        }}

        QComboBox QAbstractItemView {{
            background-color: {theme.background_secondary};
            color: {theme.text_primary};
            border: 1px solid {theme.border};
            selection-background-color: {theme.accent_subtle};
            outline: none;
        }}

        /* === LIST WIDGET === */
        QListWidget {{
            background-color: {theme.background_secondary};
            color: {theme.text_primary};
            border: 1px solid {theme.border_subtle};
            border-radius: {metrics.radius_small}px;
            font-size: {metrics.font_small}px;
            outline: none;
        }}

        QListWidget::item {{
            padding: {metrics.padding_small}px;
            border-radius: {metrics.radius_small}px;
        }}

        QListWidget::item:selected {{
            background-color: {theme.accent_subtle};
        }}

        QListWidget::item:hover {{
            background-color: {theme.border_subtle};
        }}

        /* === PROGRESS BAR === */
        QProgressBar {{
            background-color: {theme.background_tertiary};
            border: none;
            border-radius: {metrics.radius_small}px;
            height: 6px;
            text-align: center;
        }}

        QProgressBar::chunk {{
            background-color: {theme.budget_green};
            border-radius: {metrics.radius_small}px;
        }}

        /* === DIALOGS === */
        QDialog {{
            background-color: {theme.background};
            border: 1px solid {theme.border};
            border-radius: {metrics.radius_large}px;
        }}

        /* === MENU === */
        QMenu {{
            background-color: {theme.background_secondary};
            color: {theme.text_primary};
            border: 1px solid {theme.border};
            border-radius: {metrics.radius_small}px;
            padding: 4px;
        }}

        QMenu::item {{
            padding: 6px 24px 6px 12px;
            border-radius: {metrics.radius_small}px;
        }}

        QMenu::item:selected {{
            background-color: {theme.accent_subtle};
        }}

        /* === CHECK BOX === */
        QCheckBox {{
            color: {theme.text_primary};
            spacing: 8px;
        }}

        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border-radius: {metrics.radius_small}px;
            border: 1px solid {theme.border};
            background-color: {theme.background_secondary};
        }}

        QCheckBox::indicator:checked {{
            background-color: {theme.accent};
            border-color: {theme.accent};
        }}

        QCheckBox::indicator:hover {{
            border-color: {theme.accent};
        }}
    """
