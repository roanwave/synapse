"""Sidebar panel with model selector and settings."""

from typing import List
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QLabel,
    QProgressBar,
    QPushButton,
    QFrame,
    QListWidget,
    QListWidgetItem,
    QFileDialog,
    QMenu,
)
from PySide6.QtCore import Qt, Signal

from ..config.themes import theme, fonts, metrics
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
        layout.setContentsMargins(
            metrics.padding_medium,
            metrics.padding_medium,
            metrics.padding_medium,
            metrics.padding_medium,
        )
        layout.setSpacing(metrics.padding_small)

        # Label
        label = QLabel("Model")
        label.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_secondary};
                font-size: {metrics.font_small}px;
                font-weight: 600;
                font-family: {fonts.ui};
                text-transform: uppercase;
                letter-spacing: 0.5px;
                background: transparent;
            }}
        """)
        layout.addWidget(label)

        # Dropdown
        self.combo = QComboBox()
        self.combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {theme.background};
                color: {theme.text_primary};
                border: 1px solid {theme.border};
                border-radius: {metrics.radius_medium}px;
                padding: {metrics.padding_medium}px {metrics.padding_medium}px;
                min-height: 24px;
                font-family: {fonts.ui};
                font-size: {metrics.font_normal}px;
            }}
            QComboBox:hover {{
                border-color: {theme.accent};
            }}
            QComboBox:focus {{
                border-color: {theme.accent};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {theme.text_secondary};
                margin-right: {metrics.padding_small}px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {theme.background_secondary};
                color: {theme.text_primary};
                border: 1px solid {theme.border};
                border-radius: {metrics.radius_small}px;
                selection-background-color: {theme.accent};
                outline: none;
                padding: {metrics.padding_small}px;
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
                border-radius: {metrics.radius_medium}px;
            }}
        """)

    def _populate_models(self) -> None:
        """Populate the dropdown with available models."""
        self.combo.clear()

        available = get_available_models()

        # Group by provider
        providers = {"anthropic": [], "openai": [], "openrouter": [], "gabai": []}
        for model in available:
            providers[model.provider].append(model)

        # Add models grouped by provider
        provider_names = {
            "anthropic": "Anthropic",
            "openai": "OpenAI",
            "openrouter": "OpenRouter",
            "gabai": "Gab AI",
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
        layout.setContentsMargins(
            metrics.padding_medium,
            metrics.padding_medium,
            metrics.padding_medium,
            metrics.padding_medium,
        )
        layout.setSpacing(metrics.padding_small)

        # Label
        label = QLabel("Context Budget")
        label.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_secondary};
                font-size: {metrics.font_small}px;
                font-weight: 600;
                font-family: {fonts.ui};
                text-transform: uppercase;
                letter-spacing: 0.5px;
                background: transparent;
            }}
        """)
        layout.addWidget(label)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        self._update_progress_style(0)
        layout.addWidget(self.progress)

        # Token count label
        self.token_label = QLabel("0 / 0 tokens")
        self.token_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_muted};
                font-size: {metrics.font_small}px;
                font-family: {fonts.mono};
                background: transparent;
            }}
        """)
        layout.addWidget(self.token_label)

        # Style the frame
        self.setStyleSheet(f"""
            ContextBudgetIndicator {{
                background-color: {theme.background_secondary};
                border-radius: {metrics.radius_medium}px;
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

        Uses gradient: green (< 50%) → yellow (50-70%) → orange (70-85%) → red (85%+)

        Args:
            percentage: Current percentage
        """
        if percentage >= 85:
            color = theme.budget_red
        elif percentage >= 70:
            color = theme.budget_orange
        elif percentage >= 50:
            color = theme.budget_yellow
        else:
            color = theme.budget_green

        self.progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {theme.background_tertiary};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 3px;
            }}
        """)


class DocumentPanel(QFrame):
    """Document attachment panel for RAG."""

    document_added = Signal(str)  # Emits file path
    document_removed = Signal(str)  # Emits doc_id
    documents_cleared = Signal()  # Emits when all documents cleared

    def __init__(self, parent: QWidget | None = None):
        """Initialize the document panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._documents: List[dict] = []  # {doc_id, name, path}
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the document panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            metrics.padding_medium,
            metrics.padding_medium,
            metrics.padding_medium,
            metrics.padding_medium,
        )
        layout.setSpacing(metrics.padding_small)

        # Label
        label = QLabel("Documents")
        label.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_secondary};
                font-size: {metrics.font_small}px;
                font-weight: 600;
                font-family: {fonts.ui};
                text-transform: uppercase;
                letter-spacing: 0.5px;
                background: transparent;
            }}
        """)
        layout.addWidget(label)

        # Document list
        self.doc_list = QListWidget()
        self.doc_list.setMaximumHeight(120)
        self.doc_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {theme.background};
                color: {theme.text_primary};
                border: 1px solid {theme.border};
                border-radius: {metrics.radius_small}px;
                font-size: {metrics.font_small}px;
                font-family: {fonts.ui};
            }}
            QListWidget::item {{
                padding: {metrics.padding_small}px;
                border-radius: {metrics.radius_small}px;
            }}
            QListWidget::item:selected {{
                background-color: {theme.accent};
            }}
            QListWidget::item:hover {{
                background-color: {theme.background_tertiary};
            }}
        """)
        self.doc_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.doc_list.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.doc_list)

        # Button row
        button_row = QHBoxLayout()
        button_row.setSpacing(metrics.padding_small)

        # Add button
        self.add_button = QPushButton("+ Add")
        self.add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {theme.text_secondary};
                border: 1px dashed {theme.border};
                border-radius: {metrics.radius_small}px;
                padding: {metrics.padding_small}px;
                font-size: {metrics.font_small}px;
                font-family: {fonts.ui};
            }}
            QPushButton:hover {{
                background-color: {theme.background_tertiary};
                color: {theme.text_primary};
                border-color: {theme.accent};
            }}
        """)
        self.add_button.clicked.connect(self._on_add_clicked)
        button_row.addWidget(self.add_button)

        # Clear all button
        self.clear_button = QPushButton("Clear All")
        self.clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {theme.text_muted};
                border: 1px solid {theme.border};
                border-radius: {metrics.radius_small}px;
                padding: {metrics.padding_small}px;
                font-size: {metrics.font_small}px;
                font-family: {fonts.ui};
            }}
            QPushButton:hover {{
                background-color: {theme.background_tertiary};
                color: {theme.error};
                border-color: {theme.error};
            }}
        """)
        self.clear_button.clicked.connect(self._on_clear_clicked)
        button_row.addWidget(self.clear_button)

        layout.addLayout(button_row)

        # Style the frame
        self.setStyleSheet(f"""
            DocumentPanel {{
                background-color: {theme.background_secondary};
                border-radius: {metrics.radius_medium}px;
            }}
        """)

    def _on_add_clicked(self) -> None:
        """Handle add document button click."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Document",
            "",
            "Documents (*.pdf *.txt *.md *.docx);;All Files (*.*)"
        )
        if file_path:
            self.document_added.emit(file_path)

    def _on_clear_clicked(self) -> None:
        """Handle clear all documents button click."""
        if self._documents:
            self.clear()
            self.documents_cleared.emit()

    def _show_context_menu(self, pos) -> None:
        """Show context menu for document list."""
        item = self.doc_list.itemAt(pos)
        if not item:
            return

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {theme.background_secondary};
                color: {theme.text_primary};
                border: 1px solid {theme.border};
                border-radius: {metrics.radius_small}px;
                padding: {metrics.padding_small}px;
                font-family: {fonts.ui};
                font-size: {metrics.font_normal}px;
            }}
            QMenu::item {{
                padding: {metrics.padding_small}px {metrics.padding_medium}px;
                border-radius: {metrics.radius_small}px;
            }}
            QMenu::item:selected {{
                background-color: {theme.accent};
            }}
        """)

        remove_action = menu.addAction("Remove")
        action = menu.exec_(self.doc_list.mapToGlobal(pos))

        if action == remove_action:
            doc_id = item.data(Qt.ItemDataRole.UserRole)
            if doc_id:
                self.document_removed.emit(doc_id)
                self._remove_document(doc_id)

    def add_document(self, doc_id: str, name: str, path: str) -> None:
        """Add a document to the list.

        Args:
            doc_id: Document ID
            name: Display name
            path: File path
        """
        self._documents.append({
            "doc_id": doc_id,
            "name": name,
            "path": path
        })

        item = QListWidgetItem(name)
        item.setData(Qt.ItemDataRole.UserRole, doc_id)
        item.setToolTip(path)
        self.doc_list.addItem(item)

    def _remove_document(self, doc_id: str) -> None:
        """Remove a document from the list.

        Args:
            doc_id: Document ID to remove
        """
        for i, doc in enumerate(self._documents):
            if doc["doc_id"] == doc_id:
                self._documents.pop(i)
                self.doc_list.takeItem(i)
                break

    def get_document_count(self) -> int:
        """Get the number of attached documents."""
        return len(self._documents)

    def clear(self) -> None:
        """Clear all documents."""
        self._documents.clear()
        self.doc_list.clear()


class Sidebar(QWidget):
    """Sidebar panel with model selector, context indicator, and document panel."""

    model_changed = Signal(str)  # Emits model_id
    regenerate_requested = Signal()
    document_added = Signal(str)  # Emits file path
    document_removed = Signal(str)  # Emits doc_id
    documents_cleared = Signal()  # Emits when all documents cleared
    inspector_toggled = Signal(bool)  # Emits visibility state

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
        layout.setContentsMargins(
            metrics.padding_medium,
            metrics.padding_medium,
            metrics.padding_medium,
            metrics.padding_medium,
        )
        layout.setSpacing(metrics.padding_medium)

        # Model selector
        self.model_selector = ModelSelector()
        self.model_selector.model_changed.connect(self.model_changed)
        layout.addWidget(self.model_selector)

        # Context budget indicator
        self.context_indicator = ContextBudgetIndicator()
        layout.addWidget(self.context_indicator)

        # Document panel
        self.document_panel = DocumentPanel()
        self.document_panel.document_added.connect(self.document_added)
        self.document_panel.document_removed.connect(self.document_removed)
        self.document_panel.documents_cleared.connect(self.documents_cleared)
        layout.addWidget(self.document_panel)

        # Regenerate button
        self.regenerate_button = QPushButton("Regenerate (Ctrl+R)")
        self.regenerate_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.regenerate_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.background_secondary};
                color: {theme.text_primary};
                border: 1px solid {theme.border};
                border-radius: {metrics.radius_medium}px;
                padding: {metrics.padding_medium}px {metrics.padding_medium}px;
                font-size: {metrics.font_normal}px;
                font-family: {fonts.ui};
            }}
            QPushButton:hover {{
                background-color: {theme.background_tertiary};
                border-color: {theme.accent};
            }}
            QPushButton:pressed {{
                background-color: {theme.accent_pressed};
            }}
            QPushButton:disabled {{
                color: {theme.text_muted};
                background-color: {theme.background_tertiary};
            }}
        """)
        self.regenerate_button.clicked.connect(self.regenerate_requested)
        layout.addWidget(self.regenerate_button)

        # Inspector toggle button
        self.inspector_button = QPushButton("Inspector (Ctrl+I)")
        self.inspector_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._inspector_active = False
        self._update_inspector_button_style()
        self.inspector_button.clicked.connect(self._on_inspector_toggle)
        layout.addWidget(self.inspector_button)

        # Push remaining space to bottom
        layout.addStretch()

        # Set width
        self.setFixedWidth(240)

        # Style
        self.setStyleSheet(f"""
            Sidebar {{
                background-color: {theme.background_tertiary};
                border-right: 1px solid {theme.border};
            }}
        """)

    def _on_inspector_toggle(self) -> None:
        """Handle inspector toggle button click."""
        self._inspector_active = not self._inspector_active
        self._update_inspector_button_style()
        self.inspector_toggled.emit(self._inspector_active)

    def _update_inspector_button_style(self) -> None:
        """Update inspector button style based on state."""
        if self._inspector_active:
            self.inspector_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme.accent};
                    color: white;
                    border: none;
                    border-radius: {metrics.radius_medium}px;
                    padding: {metrics.padding_medium}px {metrics.padding_medium}px;
                    font-size: {metrics.font_normal}px;
                    font-family: {fonts.ui};
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: {theme.accent_hover};
                }}
            """)
        else:
            self.inspector_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme.background_secondary};
                    color: {theme.text_secondary};
                    border: 1px solid {theme.border};
                    border-radius: {metrics.radius_medium}px;
                    padding: {metrics.padding_medium}px {metrics.padding_medium}px;
                    font-size: {metrics.font_normal}px;
                    font-family: {fonts.ui};
                }}
                QPushButton:hover {{
                    background-color: {theme.background_tertiary};
                    color: {theme.text_primary};
                    border-color: {theme.accent};
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

    def add_document(self, doc_id: str, name: str, path: str) -> None:
        """Add a document to the document panel.

        Args:
            doc_id: Document ID
            name: Display name
            path: File path
        """
        self.document_panel.add_document(doc_id, name, path)

    def set_inspector_active(self, active: bool) -> None:
        """Set the inspector button active state.

        Args:
            active: Whether inspector is visible
        """
        self._inspector_active = active
        self._update_inspector_button_style()
