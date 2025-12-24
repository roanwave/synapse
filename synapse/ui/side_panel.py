"""Side panel for quick questions without polluting main conversation."""

from typing import Optional
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QTextEdit,
    QScrollArea,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QKeyEvent

from ..config.themes import theme, fonts, metrics


class SideInputPanel(QFrame):
    """Input panel for side questions."""

    message_submitted = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        """Initialize the side input panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the input panel UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            metrics.padding_medium,
            metrics.padding_medium,
            metrics.padding_medium,
            metrics.padding_medium,
        )
        layout.setSpacing(metrics.padding_small)

        # Text input
        self._input = QTextEdit()
        self._input.setPlaceholderText("Ask a quick side question...")
        self._input.setMaximumHeight(80)
        self._input.setStyleSheet(f"""
            QTextEdit {{
                background-color: {theme.background_elevated};
                color: {theme.text_primary};
                border: 1px solid {theme.border};
                border-radius: {metrics.radius_medium}px;
                padding: {metrics.padding_small}px;
                font-size: {metrics.font_normal}px;
                font-family: {fonts.chat};
            }}
            QTextEdit:focus {{
                border: 2px solid {theme.accent};
            }}
        """)
        self._input.installEventFilter(self)
        layout.addWidget(self._input, stretch=1)

        # Send button
        self._send_btn = QPushButton("Ask")
        self._send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.accent};
                color: white;
                border: none;
                border-radius: {metrics.radius_medium}px;
                padding: {metrics.padding_medium}px {metrics.padding_large}px;
                font-size: {metrics.font_normal}px;
                font-family: {fonts.ui};
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {theme.accent_hover};
            }}
            QPushButton:disabled {{
                background-color: {theme.text_disabled};
            }}
        """)
        self._send_btn.clicked.connect(self._on_send)
        layout.addWidget(self._send_btn)

        self.setStyleSheet(f"""
            SideInputPanel {{
                background-color: {theme.background_tertiary};
                border-top: 1px solid {theme.border_subtle};
            }}
        """)

    def eventFilter(self, obj, event) -> bool:
        """Handle key events for Enter to send."""
        if obj == self._input and isinstance(event, QKeyEvent):
            if event.key() == Qt.Key.Key_Return and not event.modifiers():
                self._on_send()
                return True
        return super().eventFilter(obj, event)

    def _on_send(self) -> None:
        """Handle send button click."""
        text = self._input.toPlainText().strip()
        if text:
            self.message_submitted.emit(text)
            self._input.clear()

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the input.

        Args:
            enabled: Whether to enable
        """
        self._input.setEnabled(enabled)
        self._send_btn.setEnabled(enabled)

    def focus_input(self) -> None:
        """Focus the input field."""
        self._input.setFocus()


class SideMessageBubble(QFrame):
    """Simple message bubble for side panel."""

    def __init__(
        self,
        role: str,
        content: str,
        parent: QWidget | None = None
    ):
        """Initialize the message bubble.

        Args:
            role: "user" or "assistant"
            content: Message content
            parent: Parent widget
        """
        super().__init__(parent)
        self.role = role
        self._setup_ui(content)

    def _setup_ui(self, content: str) -> None:
        """Set up the bubble UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            metrics.padding_medium,
            metrics.padding_small,
            metrics.padding_medium,
            metrics.padding_small,
        )
        layout.setSpacing(2)

        # Role label
        role_text = "You" if self.role == "user" else "Side"
        role_label = QLabel(role_text)
        role_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_muted};
                font-size: 10px;
                font-weight: 600;
                font-family: {fonts.ui};
            }}
        """)
        layout.addWidget(role_label)

        # Content
        content_label = QLabel(content)
        content_label.setWordWrap(True)
        content_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        if self.role == "user":
            bg_color = theme.user_bubble_start
            text_color = "#ffffff"
        else:
            bg_color = theme.background_elevated
            text_color = theme.text_primary

        content_label.setStyleSheet(f"""
            QLabel {{
                color: {text_color};
                font-size: {metrics.font_normal}px;
                font-family: {fonts.chat};
                padding: {metrics.padding_small}px;
                background-color: {bg_color};
                border-radius: {metrics.radius_medium}px;
            }}
        """)
        layout.addWidget(content_label)

        self.setStyleSheet("SideMessageBubble { background: transparent; }")


class SidePanel(QFrame):
    """Floating side panel for quick questions."""

    # Signals
    closed = Signal()
    merge_requested = Signal()  # User wants to merge insights

    def __init__(self, parent: QWidget | None = None):
        """Initialize the side panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the panel UI."""
        self.setMinimumWidth(400)
        self.setMaximumWidth(500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.background_tertiary};
                border-bottom: 1px solid {theme.border_subtle};
            }}
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(
            metrics.padding_large,
            metrics.padding_medium,
            metrics.padding_large,
            metrics.padding_medium,
        )
        header_layout.setSpacing(metrics.padding_medium)

        # Title
        title = QLabel("SIDE QUESTION")
        title.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_muted};
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 1px;
                font-family: {fonts.ui};
            }}
        """)
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Merge button
        self._merge_btn = QPushButton("Merge")
        self._merge_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._merge_btn.setToolTip("Merge insights into main conversation")
        self._merge_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {theme.text_muted};
                border: 1px solid {theme.border};
                border-radius: {metrics.radius_small}px;
                padding: 4px 12px;
                font-size: 11px;
                font-family: {fonts.ui};
            }}
            QPushButton:hover {{
                background-color: {theme.background_elevated};
                color: {theme.success};
                border-color: {theme.success};
            }}
        """)
        self._merge_btn.clicked.connect(self.merge_requested)
        header_layout.addWidget(self._merge_btn)

        # Close button
        close_btn = QPushButton("✕")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {theme.text_muted};
                border: none;
                font-size: 14px;
            }}
            QPushButton:hover {{
                color: {theme.error};
            }}
        """)
        close_btn.clicked.connect(self.closed)
        header_layout.addWidget(close_btn)

        layout.addWidget(header)

        # Messages area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {theme.background_secondary};
                border: none;
            }}
            QScrollBar:vertical {{
                background: {theme.background_secondary};
                width: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: {theme.border};
                border-radius: 3px;
                min-height: 20px;
            }}
        """)

        self._messages_container = QWidget()
        self._messages_container.setStyleSheet(f"""
            QWidget {{
                background-color: {theme.background_secondary};
            }}
        """)
        self._messages_layout = QVBoxLayout(self._messages_container)
        self._messages_layout.setContentsMargins(
            metrics.padding_medium,
            metrics.padding_medium,
            metrics.padding_medium,
            metrics.padding_medium,
        )
        self._messages_layout.setSpacing(metrics.padding_small)
        self._messages_layout.addStretch()

        scroll.setWidget(self._messages_container)
        self._scroll_area = scroll
        layout.addWidget(scroll, stretch=1)

        # Input panel
        self.input_panel = SideInputPanel()
        layout.addWidget(self.input_panel)

        # Panel styling
        self.setStyleSheet(f"""
            SidePanel {{
                background-color: {theme.background_secondary};
                border-left: 1px solid {theme.border};
            }}
        """)

    def add_user_message(self, content: str) -> None:
        """Add a user message to the panel.

        Args:
            content: Message content
        """
        bubble = SideMessageBubble("user", content)
        self._add_bubble(bubble)

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message to the panel.

        Args:
            content: Message content
        """
        bubble = SideMessageBubble("assistant", content)
        self._add_bubble(bubble)

    def start_assistant_message(self) -> None:
        """Start an assistant message (show typing indicator)."""
        # For now, just add a placeholder that will be replaced
        pass

    def append_to_assistant_message(self, text: str) -> None:
        """Append text to current assistant message.

        For side panel, we accumulate until finish.
        """
        pass

    def finish_assistant_message(self, full_content: str) -> None:
        """Finish assistant message with full content.

        Args:
            full_content: Complete message content
        """
        self.add_assistant_message(full_content)

    def _add_bubble(self, bubble: SideMessageBubble) -> None:
        """Add a bubble to the messages layout.

        Args:
            bubble: The message bubble to add
        """
        # Remove stretch
        stretch_item = self._messages_layout.takeAt(
            self._messages_layout.count() - 1
        )

        self._messages_layout.addWidget(bubble)
        self._messages_layout.addStretch()

        # Scroll to bottom
        QTimer.singleShot(10, self._scroll_to_bottom)

    def _scroll_to_bottom(self) -> None:
        """Scroll to bottom of messages."""
        scrollbar = self._scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear(self) -> None:
        """Clear all messages."""
        while self._messages_layout.count() > 1:
            item = self._messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def set_input_enabled(self, enabled: bool) -> None:
        """Enable or disable input.

        Args:
            enabled: Whether to enable
        """
        self.input_panel.set_enabled(enabled)

    def focus_input(self) -> None:
        """Focus the input field."""
        self.input_panel.focus_input()
