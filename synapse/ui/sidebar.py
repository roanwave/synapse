"""Sidebar panel with model selector and settings."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QLabel,
    QProgressBar,
    QPushButton,
    QFrame,
)
from PySide6.QtCore import Qt, Signal

from ..config.themes import theme
from ..config.models import MODELS, get_available_models, ModelConfig


class ModelSelector(QFrame):
    """Model selection dropdown with provider grouping."""

    model_changed = Signal(str)  # Emits model_id

    def __init__(self, parent: QWidget | None = None):
        """Initialize the model selector.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._current_model_id: str = ""
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the selector UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Label
        label = QLabel("Model")
        label.setStyleSheet(f"""
            color: {theme.text_secondary};
            font-size: 11px;
            font-weight: bold;
            text-transform: uppercase;
            background: transparent;
        """)
        layout.addWidget(label)

        # Dropdown
        self.combo = QComboBox()
        self.combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {theme.background_secondary};
                color: {theme.text_primary};
                border: 1px solid {theme.border};
                border-radius: 6px;
                padding: 8px 12px;
                min-height: 20px;
            }}
            QComboBox:hover {{
                border-color: {theme.accent};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {theme.text_secondary};
                margin-right: 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {theme.background_secondary};
                color: {theme.text_primary};
                border: 1px solid {theme.border};
                selection-background-color: {theme.accent};
                outline: none;
            }}
        """)
        self.combo.currentIndexChanged.connect(self._on_selection_changed)
        layout.addWidget(self.combo)

        # Populate with available models
        self._populate_models()

        # Style the frame
        self.setStyleSheet(f"""
            ModelSelector {{
                background-color: {theme.background_secondary};
                border-radius: 8px;
            }}
        """)

    def _populate_models(self) -> None:
        """Populate the dropdown with available models."""
        self.combo.clear()

        available = get_available_models()

        # Group by provider
        providers = {"anthropic": [], "openai": [], "openrouter": []}
        for model in available:
            providers[model.provider].append(model)

        # Add models grouped by provider
        provider_names = {
            "anthropic": "Anthropic",
            "openai": "OpenAI",
            "openrouter": "OpenRouter",
        }

        for provider_id, models in providers.items():
            if models:
                # Add separator/header for provider
                self.combo.addItem(f"── {provider_names[provider_id]} ──", None)
                # Make header non-selectable
                idx = self.combo.count() - 1
                self.combo.model().item(idx).setEnabled(False)

                for model in models:
                    self.combo.addItem(model.display_name, model.model_id)

        # If no models available, show message
        if self.combo.count() == 0:
            self.combo.addItem("No API keys configured", None)
            self.combo.setEnabled(False)

    def set_model(self, model_id: str) -> None:
        """Set the currently selected model.

        Args:
            model_id: The model ID to select
        """
        for i in range(self.combo.count()):
            if self.combo.itemData(i) == model_id:
                self.combo.setCurrentIndex(i)
                self._current_model_id = model_id
                return

    def get_model(self) -> str | None:
        """Get the currently selected model ID.

        Returns:
            Model ID or None if no valid selection
        """
        return self.combo.currentData()

    def refresh(self) -> None:
        """Refresh the model list (e.g., after API keys change)."""
        current = self._current_model_id
        self._populate_models()
        if current:
            self.set_model(current)

    def _on_selection_changed(self, index: int) -> None:
        """Handle selection change."""
        model_id = self.combo.itemData(index)
        if model_id and model_id != self._current_model_id:
            self._current_model_id = model_id
            self.model_changed.emit(model_id)


class ContextBudgetIndicator(QFrame):
    """Visual indicator for context window usage."""

    def __init__(self, parent: QWidget | None = None):
        """Initialize the indicator.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the indicator UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Label
        label = QLabel("Context")
        label.setStyleSheet(f"""
            color: {theme.text_secondary};
            font-size: 11px;
            font-weight: bold;
            text-transform: uppercase;
            background: transparent;
        """)
        layout.addWidget(label)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setFormat("%p%")
        self._update_progress_style(0)
        layout.addWidget(self.progress)

        # Token count label
        self.token_label = QLabel("0 / 0 tokens")
        self.token_label.setStyleSheet(f"""
            color: {theme.text_muted};
            font-size: 11px;
            background: transparent;
        """)
        layout.addWidget(self.token_label)

        # Style the frame
        self.setStyleSheet(f"""
            ContextBudgetIndicator {{
                background-color: {theme.background_secondary};
                border-radius: 8px;
            }}
        """)

    def update(self, current: int, maximum: int) -> None:
        """Update the indicator.

        Args:
            current: Current token count
            maximum: Maximum tokens (context window)
        """
        if maximum == 0:
            percentage = 0
        else:
            percentage = int((current / maximum) * 100)

        self.progress.setValue(min(100, percentage))
        self.token_label.setText(f"{current:,} / {maximum:,} tokens")
        self._update_progress_style(percentage)

    def _update_progress_style(self, percentage: int) -> None:
        """Update progress bar color based on percentage.

        Args:
            percentage: Current percentage
        """
        if percentage >= 80:
            color = theme.warning  # Orange at 80%+
        elif percentage >= 60:
            color = "#d4a017"  # Yellow at 60%+
        else:
            color = theme.success  # Green below 60%

        self.progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {theme.background_tertiary};
                border: none;
                border-radius: 4px;
                height: 8px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 4px;
            }}
        """)


class Sidebar(QWidget):
    """Sidebar panel with model selector and context indicator."""

    model_changed = Signal(str)  # Emits model_id
    regenerate_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        """Initialize the sidebar.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the sidebar UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # Model selector
        self.model_selector = ModelSelector()
        self.model_selector.model_changed.connect(self.model_changed)
        layout.addWidget(self.model_selector)

        # Context budget indicator
        self.context_indicator = ContextBudgetIndicator()
        layout.addWidget(self.context_indicator)

        # Regenerate button
        self.regenerate_button = QPushButton("Regenerate (Ctrl+R)")
        self.regenerate_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.background_tertiary};
                color: {theme.text_primary};
                border: 1px solid {theme.border};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {theme.background_secondary};
                border-color: {theme.accent};
            }}
            QPushButton:pressed {{
                background-color: {theme.accent_pressed};
            }}
            QPushButton:disabled {{
                color: {theme.text_muted};
            }}
        """)
        self.regenerate_button.clicked.connect(self.regenerate_requested)
        layout.addWidget(self.regenerate_button)

        # Push remaining space to bottom
        layout.addStretch()

        # Set width
        self.setFixedWidth(220)

        # Style
        self.setStyleSheet(f"""
            Sidebar {{
                background-color: {theme.background_tertiary};
                border-right: 1px solid {theme.border};
            }}
        """)

    def set_model(self, model_id: str) -> None:
        """Set the currently selected model.

        Args:
            model_id: The model ID to select
        """
        self.model_selector.set_model(model_id)

    def get_model(self) -> str | None:
        """Get the currently selected model ID.

        Returns:
            Model ID or None
        """
        return self.model_selector.get_model()

    def update_context(self, current: int, maximum: int) -> None:
        """Update the context budget indicator.

        Args:
            current: Current token count
            maximum: Maximum context window
        """
        self.context_indicator.update(current, maximum)

    def set_regenerate_enabled(self, enabled: bool) -> None:
        """Enable or disable the regenerate button.

        Args:
            enabled: Whether to enable
        """
        self.regenerate_button.setEnabled(enabled)
