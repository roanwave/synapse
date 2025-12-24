"""Table of Contents panel for conversation navigation.

Displays auto-generated and manual TOC entries for jumping
to specific messages in the conversation.
"""

from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QFrame,
)
from PySide6.QtCore import Signal, Qt

from ..config.themes import theme, fonts, metrics
from ..orchestrator.toc_generator import TOCEntry


class TOCEntryWidget(QFrame):
    """Widget for a single TOC entry."""

    clicked = Signal(int)  # Emits message_index

    def __init__(
        self,
        entry: TOCEntry,
        is_current: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the TOC entry widget.

        Args:
            entry: The TOC entry data
            is_current: Whether this is the current section
            parent: Parent widget
        """
        super().__init__(parent)
        self._entry = entry
        self._is_current = is_current
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the widget UI."""
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Indent based on level
        left_margin = (self._entry.level - 1) * 12

        # Current indicator
        indicator_color = theme.accent if self._is_current else "transparent"

        self.setStyleSheet(f"""
            QFrame {{
                background-color: transparent;
                border: none;
                border-left: 3px solid {indicator_color};
                padding: 4px 8px 4px {left_margin + 8}px;
                margin: 1px 0;
            }}
            QFrame:hover {{
                background-color: {theme.background_tertiary};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Entry type icon
        icon = self._get_icon()
        if icon:
            icon_label = QLabel(icon)
            icon_label.setStyleSheet(f"""
                QLabel {{
                    color: {theme.text_muted};
                    font-size: 10px;
                }}
            """)
            layout.addWidget(icon_label)

        # Title
        title_color = theme.text_primary if self._is_current else theme.text_secondary
        title = QLabel(self._entry.title)
        title.setStyleSheet(f"""
            QLabel {{
                color: {title_color};
                font-size: {metrics.font_small}px;
                font-family: {fonts.ui};
                font-weight: {"600" if self._is_current else "400"};
            }}
        """)
        title.setWordWrap(True)
        layout.addWidget(title, stretch=1)

    def _get_icon(self) -> str:
        """Get icon based on entry type."""
        icons = {
            "waypoint": "◆",
            "heading": "§",
            "auto": "•",
        }
        return icons.get(self._entry.entry_type, "•")

    def mousePressEvent(self, event) -> None:
        """Handle mouse press."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._entry.message_index)
        super().mousePressEvent(event)


class TOCPanel(QWidget):
    """Table of Contents panel widget."""

    # Signal when user clicks to jump to a message
    jump_to_message = Signal(int)  # message_index

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the TOC panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._entries: List[TOCEntry] = []
        self._current_index: int = -1
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the panel UI."""
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {theme.background_sidebar};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.background_sidebar};
                border-bottom: 1px solid {theme.border_subtle};
                padding: 8px 12px;
            }}
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)
        header_layout.setSpacing(8)

        title = QLabel("CONTENTS")
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
        header_layout.addStretch()

        layout.addWidget(header)

        # Scroll area for entries
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {theme.background_sidebar};
                border: none;
            }}
            QScrollBar:vertical {{
                background: {theme.background_sidebar};
                width: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: {theme.border};
                border-radius: 3px;
                min-height: 20px;
            }}
        """)

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(4, 4, 4, 4)
        self._content_layout.setSpacing(0)
        self._content_layout.addStretch()

        scroll.setWidget(self._content)
        layout.addWidget(scroll, stretch=1)

        # Empty state
        self._empty_label = QLabel("No sections yet")
        self._empty_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_muted};
                font-size: {metrics.font_small}px;
                font-family: {fonts.ui};
                padding: 20px;
            }}
        """)
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._content_layout.insertWidget(0, self._empty_label)

    def set_entries(self, entries: List[TOCEntry]) -> None:
        """Set the TOC entries.

        Args:
            entries: List of TOC entries
        """
        self._entries = entries
        self._rebuild_entries()

    def set_current_index(self, message_index: int) -> None:
        """Set the current message index for highlighting.

        Args:
            message_index: Current message index
        """
        self._current_index = message_index
        self._rebuild_entries()

    def add_entry(self, entry: TOCEntry) -> None:
        """Add a single entry to the TOC.

        Args:
            entry: The entry to add
        """
        self._entries.append(entry)
        self._entries.sort(key=lambda e: e.message_index)
        self._rebuild_entries()

    def _rebuild_entries(self) -> None:
        """Rebuild the entry widgets."""
        # Clear existing entries (except stretch)
        while self._content_layout.count() > 1:
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Show/hide empty state
        self._empty_label.setVisible(len(self._entries) == 0)

        if not self._entries:
            self._content_layout.insertWidget(0, self._empty_label)
            return

        # Find current section
        current_entry = None
        for entry in self._entries:
            if entry.message_index <= self._current_index:
                current_entry = entry

        # Add entry widgets
        for i, entry in enumerate(self._entries):
            is_current = entry == current_entry
            widget = TOCEntryWidget(entry, is_current)
            widget.clicked.connect(self._on_entry_clicked)
            self._content_layout.insertWidget(i, widget)

    def _on_entry_clicked(self, message_index: int) -> None:
        """Handle entry click.

        Args:
            message_index: Index of message to jump to
        """
        self.jump_to_message.emit(message_index)

    def clear(self) -> None:
        """Clear all entries."""
        self._entries.clear()
        self._current_index = -1
        self._rebuild_entries()
