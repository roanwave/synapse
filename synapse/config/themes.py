"""Premium dark theme for Synapse.

Premium aesthetic inspired by Linear, Raycast, Arc Browser, and Stripe.
"""

from dataclasses import dataclass


@dataclass
class ThemeColors:
    """Premium color scheme - $100/month SaaS aesthetic.

    Deep, rich colors with purposeful accents and subtle depth.
    """

    # Background layers (create depth through subtle variation)
    background: str = "#0a0a0f"  # App background - almost black, slight blue tint
    background_secondary: str = "#121218"  # Chat panel - elevated layer
    background_tertiary: str = "#0d0d12"  # Sidebar - recessed slightly
    background_sidebar: str = "#0d0d12"  # Sidebar and side panels (alias)
    background_elevated: str = "#1a1a22"  # Modals, dropdowns, cards

    # Text hierarchy
    text_primary: str = "#f9fafb"  # Almost white, readable
    text_secondary: str = "#d1d5db"  # Lighter gray
    text_muted: str = "#9ca3af"  # Muted gray
    text_disabled: str = "#6b7280"  # Very muted

    # Accent colors (purposeful and premium)
    accent: str = "#6366f1"  # Primary indigo - professional, trustworthy
    accent_hover: str = "#818cf8"  # Lighter indigo
    accent_pressed: str = "#4f46e5"  # Darker indigo
    accent_subtle: str = "rgba(99, 102, 241, 0.15)"  # Very subtle accent
    accent_glow: str = "rgba(99, 102, 241, 0.4)"  # For shadows/glows

    # Secondary accent
    secondary: str = "#8b5cf6"  # Purple - creative, premium

    # Border colors
    border: str = "#374151"  # Visible but not harsh
    border_subtle: str = "#1f2937"  # Barely visible separation
    border_focus: str = "#6366f1"  # Accent color for focus

    # Status colors
    success: str = "#10b981"  # Emerald
    success_light: str = "#34d399"
    warning: str = "#f59e0b"  # Amber
    warning_light: str = "#fbbf24"
    error: str = "#ef4444"  # Red
    error_light: str = "#f87171"

    # Token budget colors (gradient progression)
    budget_green: str = "#10b981"
    budget_green_light: str = "#34d399"
    budget_yellow: str = "#f59e0b"
    budget_yellow_light: str = "#fbbf24"
    budget_orange: str = "#fb923c"
    budget_orange_light: str = "#f97316"
    budget_red: str = "#ef4444"
    budget_red_light: str = "#dc2626"

    # Message bubble colors
    user_bubble_start: str = "#6366f1"  # Gradient start
    user_bubble_end: str = "#8b5cf6"  # Gradient end
    assistant_bubble: str = "#1a1a22"

    # Scrollbar (minimal, premium)
    scrollbar_bg: str = "transparent"
    scrollbar_handle: str = "#374151"
    scrollbar_handle_hover: str = "#4b5563"

    # Selection
    selection: str = "rgba(99, 102, 241, 0.3)"

    # Code block (GitHub dark inspired)
    code_bg: str = "#0d1117"
    code_border: str = "#30363d"


@dataclass
class ThemeFonts:
    """Premium font families."""

    # UI elements - Inter is the premium standard
    ui: str = "'Inter', 'SF Pro Display', -apple-system, system-ui, sans-serif"

    # Chat messages
    chat: str = "'Inter', 'SF Pro Text', 'Segoe UI', sans-serif"

    # Code and monospace
    mono: str = "'JetBrains Mono', 'Fira Code', 'Consolas', monospace"


@dataclass
class ThemeMetrics:
    """Spacing and sizing - premium proportions."""

    # Border radius (slightly larger for premium feel)
    radius_small: int = 6
    radius_medium: int = 8
    radius_large: int = 12
    radius_xl: int = 16

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

    # Shadows
    shadow_sm: str = "0 2px 8px rgba(0, 0, 0, 0.3)"
    shadow_md: str = "0 4px 12px rgba(0, 0, 0, 0.4)"
    shadow_lg: str = "0 8px 24px rgba(0, 0, 0, 0.5)"
    shadow_accent: str = "0 4px 16px rgba(99, 102, 241, 0.4)"
    shadow_user_bubble: str = "0 4px 12px rgba(99, 102, 241, 0.15)"

    # Transitions
    transition_fast: str = "150ms cubic-bezier(0.4, 0, 0.2, 1)"
    transition_normal: str = "200ms cubic-bezier(0.4, 0, 0.2, 1)"
    transition_slow: str = "300ms cubic-bezier(0.4, 0, 0.2, 1)"


# Global instances
theme = ThemeColors()
fonts = ThemeFonts()
metrics = ThemeMetrics()


def get_stylesheet() -> str:
    """Generate the complete premium application stylesheet.

    Returns:
        CSS stylesheet string for Qt
    """
    return f"""
        /* === GLOBAL - Premium Dark === */
        QMainWindow {{
            background-color: {theme.background};
        }}

        QWidget {{
            background-color: {theme.background};
            color: {theme.text_primary};
            font-family: {fonts.ui};
            font-size: {metrics.font_normal}px;
        }}

        /* === SCROLL AREAS - Minimal Premium === */
        QScrollArea {{
            background-color: transparent;
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

        /* === TEXT INPUTS - Premium Elevated === */
        QTextEdit {{
            background-color: {theme.background_elevated};
            color: {theme.text_primary};
            border: 1px solid {theme.border};
            border-radius: {metrics.radius_large}px;
            padding: {metrics.padding_medium}px {metrics.padding_large}px;
            selection-background-color: {theme.selection};
            font-family: {fonts.chat};
            font-size: {metrics.font_medium}px;
        }}

        QTextEdit:focus {{
            border: 2px solid {theme.border_focus};
        }}

        QTextEdit:disabled {{
            background-color: {theme.background_tertiary};
            color: {theme.text_disabled};
            border-color: {theme.border_subtle};
        }}

        /* === BUTTONS - Premium with Depth === */
        QPushButton {{
            background-color: {theme.accent};
            color: white;
            border: none;
            border-radius: {metrics.radius_medium}px;
            padding: {metrics.padding_small}px {metrics.padding_large}px;
            font-weight: 500;
            font-family: {fonts.ui};
            font-size: {metrics.font_normal}px;
        }}

        QPushButton:hover {{
            background-color: {theme.accent_hover};
        }}

        QPushButton:pressed {{
            background-color: {theme.accent_pressed};
        }}

        QPushButton:disabled {{
            background-color: {theme.border};
            color: {theme.text_disabled};
        }}

        /* === LABELS === */
        QLabel {{
            background-color: transparent;
            color: {theme.text_primary};
            font-family: {fonts.ui};
        }}

        /* === STATUS BAR - Subtle Premium === */
        QStatusBar {{
            background-color: {theme.background_tertiary};
            color: {theme.text_muted};
            border-top: 1px solid {theme.border_subtle};
            font-size: {metrics.font_small}px;
        }}

        /* === COMBO BOX - Premium Dropdown === */
        QComboBox {{
            background-color: {theme.background_elevated};
            color: {theme.text_primary};
            border: 1px solid {theme.border};
            border-radius: {metrics.radius_medium}px;
            padding: {metrics.padding_medium}px;
            min-height: 24px;
            font-family: {fonts.ui};
            font-size: {metrics.font_normal}px;
        }}

        QComboBox:hover {{
            border-color: {theme.accent};
        }}

        QComboBox:focus {{
            border: 2px solid {theme.border_focus};
        }}

        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}

        QComboBox::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid {theme.text_muted};
            margin-right: {metrics.padding_small}px;
        }}

        QComboBox QAbstractItemView {{
            background-color: {theme.background_elevated};
            color: {theme.text_primary};
            border: 1px solid {theme.border};
            border-radius: {metrics.radius_medium}px;
            selection-background-color: {theme.accent};
            outline: none;
            padding: {metrics.padding_small}px;
        }}

        /* === LIST WIDGET - Premium List === */
        QListWidget {{
            background-color: {theme.background};
            color: {theme.text_primary};
            border: 1px solid {theme.border};
            border-radius: {metrics.radius_medium}px;
            font-size: {metrics.font_small}px;
            outline: none;
        }}

        QListWidget::item {{
            padding: {metrics.padding_small}px {metrics.padding_medium}px;
            border-radius: {metrics.radius_small}px;
            border-left: 3px solid transparent;
        }}

        QListWidget::item:selected {{
            background-color: {theme.accent_subtle};
            border-left: 3px solid {theme.accent};
        }}

        QListWidget::item:hover {{
            background-color: {theme.background_elevated};
        }}

        /* === PROGRESS BAR - Premium Gradient === */
        QProgressBar {{
            background-color: {theme.background_elevated};
            border: 1px solid {theme.border};
            border-radius: {metrics.radius_medium}px;
            height: 6px;
            text-align: center;
        }}

        QProgressBar::chunk {{
            background-color: {theme.success};
            border-radius: 5px;
        }}

        /* === DIALOGS - Elevated Premium === */
        QDialog {{
            background-color: {theme.background_secondary};
            border: 1px solid {theme.border};
            border-radius: {metrics.radius_large}px;
        }}

        /* === MENU - Premium Dropdown === */
        QMenu {{
            background-color: {theme.background_elevated};
            color: {theme.text_primary};
            border: 1px solid {theme.border};
            border-radius: {metrics.radius_medium}px;
            padding: {metrics.padding_small}px;
        }}

        QMenu::item {{
            padding: {metrics.padding_small}px {metrics.padding_large}px;
            border-radius: {metrics.radius_small}px;
        }}

        QMenu::item:selected {{
            background-color: {theme.accent};
        }}

        QMenu::separator {{
            height: 1px;
            background-color: {theme.border_subtle};
            margin: {metrics.padding_small}px {metrics.padding_medium}px;
        }}

        /* === CHECK BOX - Premium Toggle === */
        QCheckBox {{
            color: {theme.text_primary};
            spacing: {metrics.padding_small}px;
        }}

        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border-radius: {metrics.radius_small}px;
            border: 2px solid {theme.border};
            background-color: {theme.background_elevated};
        }}

        QCheckBox::indicator:checked {{
            background-color: {theme.accent};
            border-color: {theme.accent};
        }}

        QCheckBox::indicator:hover {{
            border-color: {theme.accent};
        }}

        /* === TEXT BROWSER === */
        QTextBrowser {{
            background-color: transparent;
            border: none;
            color: {theme.text_primary};
            selection-background-color: {theme.selection};
        }}

        /* === TOOL TIP === */
        QToolTip {{
            background-color: {theme.background_elevated};
            color: {theme.text_primary};
            border: 1px solid {theme.border};
            border-radius: {metrics.radius_small}px;
            padding: {metrics.padding_small}px {metrics.padding_medium}px;
            font-size: {metrics.font_small}px;
        }}
    """
