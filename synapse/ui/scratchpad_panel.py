"""Scratchpad panel for private notes visible to the model."""

from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QTextEdit,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal

from ..config.themes import theme, fonts, metrics


class ScratchpadPanel(QFrame):
    """Collapsible scratchpad for private notes.

    Content is visible to the model in the system prompt
    but not part of the conversation history.
    """

    # Signal emitted when content changes
    content_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        """Initialize the scratchpad panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._is_collapsed = True
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header (always visible)
        self._header = QFrame()
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)
        self._header.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.background_tertiary};
                border-bottom: 1px solid {theme.border_subtle};
            }}
            QFrame:hover {{
                background-color: {theme.background_elevated};
            }}
        """)
        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(
            metrics.padding_medium,
            metrics.padding_small,
            metrics.padding_medium,
            metrics.padding_small,
        )
        header_layout.setSpacing(metrics.padding_small)

        # Collapse/expand indicator
        self._toggle_indicator = QLabel("▶")
        self._toggle_indicator.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_muted};
                font-size: 10px;
                font-family: {fonts.ui};
            }}
        """)
        header_layout.addWidget(self._toggle_indicator)

        # Title
        title = QLabel("SCRATCHPAD")
        title.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_muted};
                font-size: 10px;
                font-weight: 600;
                letter-spacing: 1px;
                font-family: {fonts.ui};
            }}
        """)
        header_layout.addWidget(title)

        # Visibility indicator
        self._visibility_label = QLabel("(visible to model)")
        self._visibility_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_disabled};
                font-size: 9px;
                font-family: {fonts.ui};
            }}
        """)
        header_layout.addWidget(self._visibility_label)
        header_layout.addStretch()

        # Clear button
        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {theme.text_disabled};
                border: none;
                font-size: 10px;
                font-family: {fonts.ui};
                padding: 2px 6px;
            }}
            QPushButton:hover {{
                color: {theme.text_muted};
            }}
        """)
        self._clear_btn.clicked.connect(self._on_clear)
        self._clear_btn.hide()  # Only visible when expanded
        header_layout.addWidget(self._clear_btn)

        layout.addWidget(self._header)

        # Content area (collapsible)
        self._content_frame = QFrame()
        self._content_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.background_tertiary};
            }}
        """)
        content_layout = QVBoxLayout(self._content_frame)
        content_layout.setContentsMargins(
            metrics.padding_medium,
            metrics.padding_small,
            metrics.padding_medium,
            metrics.padding_medium,
        )
        content_layout.setSpacing(0)

        # Text editor
        self._editor = QTextEdit()
        self._editor.setPlaceholderText(
            "Private notes visible to the model...\n"
            "Use for: outlines, decision logs, scratch work"
        )
        self._editor.setMinimumHeight(80)
        self._editor.setMaximumHeight(200)
        self._editor.setStyleSheet(f"""
            QTextEdit {{
                background-color: {theme.background_elevated};
                color: {theme.text_primary};
                border: 1px solid {theme.border_subtle};
                border-radius: {metrics.radius_small}px;
                padding: {metrics.padding_small}px;
                font-size: {metrics.font_small}px;
                font-family: {fonts.mono};
            }}
            QTextEdit:focus {{
                border-color: {theme.accent};
            }}
        """)
        self._editor.textChanged.connect(self._on_text_changed)
        content_layout.addWidget(self._editor)

        self._content_frame.hide()  # Start collapsed
        layout.addWidget(self._content_frame)

        # Frame styling
        self.setStyleSheet(f"""
            ScratchpadPanel {{
                background-color: {theme.background_tertiary};
            }}
        """)

        # Make header clickable
        self._header.mousePressEvent = self._on_header_clicked

    def _on_header_clicked(self, event) -> None:
        """Handle header click to toggle collapse."""
        self.toggle()

    def toggle(self) -> None:
        """Toggle the collapsed/expanded state."""
        self._is_collapsed = not self._is_collapsed
        self._content_frame.setVisible(not self._is_collapsed)
        self._clear_btn.setVisible(not self._is_collapsed)
        self._toggle_indicator.setText("▼" if not self._is_collapsed else "▶")

    def expand(self) -> None:
        """Expand the panel."""
        if self._is_collapsed:
            self.toggle()

    def collapse(self) -> None:
        """Collapse the panel."""
        if not self._is_collapsed:
            self.toggle()

    def _on_text_changed(self) -> None:
        """Handle text changes."""
        self.content_changed.emit(self._editor.toPlainText())

    def _on_clear(self) -> None:
        """Clear the scratchpad content."""
        self._editor.clear()

    def get_content(self) -> str:
        """Get the scratchpad content.

        Returns:
            Current scratchpad text
        """
        return self._editor.toPlainText()

    def set_content(self, content: str) -> None:
        """Set the scratchpad content.

        Args:
            content: Text to set
        """
        self._editor.blockSignals(True)
        self._editor.setPlainText(content)
        self._editor.blockSignals(False)

    def clear(self) -> None:
        """Clear the scratchpad content."""
        self._editor.clear()

    def is_empty(self) -> bool:
        """Check if scratchpad is empty.

        Returns:
            True if empty
        """
        return not self._editor.toPlainText().strip()

    def focus_editor(self) -> None:
        """Focus the editor and expand if collapsed."""
        self.expand()
        self._editor.setFocus()
